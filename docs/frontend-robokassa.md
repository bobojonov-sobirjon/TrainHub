# TrainHub — фронтенд: оплата PRO (Robokassa)

Мобильному приложению **не нужны** пароли Robokassa и Result URL.  
Подпись, webhook и активация PRO — только backend.

База: `http://51.20.92.246/api/v1/app`  
Auth: `Authorization: Bearer <access_token>` (`aud=app`)  
Конверт: `{ "success": true, "data": … }` / `{ "success": false, "error": { "code", "message" } }`

Экраны Figma: **C17** Coach (`pro_trainer`), **L15** Client (`pro_client`).

---

## 1. Что делает приложение

```
тарифы → checkout → открыть payment_url (WebView)
        → пользователь платит на Robokassa
        → редирект /pay/success или /pay/fail
        → закрыть WebView
        → опросить подписку, пока status != active
```

PRO **не** ставить по факту открытия `/pay/success`.  
Банк ещё шлёт Result URL на сервер. Сервер отвечает `OK{InvId}` и только тогда `subscription.status = active`.

| Кто | Задача |
|-----|--------|
| Frontend | тариф, checkout, WebView, polling |
| Backend | подпись, webhook, PRO |
| Не вызывать | `POST /webhooks/payments/robokassa` |

---

## 2. Тарифы

`GET /plans?audience=pro_trainer` — Coach  
`GET /plans?audience=pro_client` — Client

```json
{
  "success": true,
  "data": [
    {
      "id": 3,
      "audience": "pro_trainer",
      "code": "trainer_pro_month",
      "period": "month",
      "price_amount": "999.00",
      "currency": "RUB",
      "discount_pct": 0
    },
    {
      "id": 4,
      "audience": "pro_trainer",
      "code": "trainer_pro_year",
      "period": "year",
      "price_amount": "8990.00",
      "currency": "RUB",
      "discount_pct": 25
    }
  ]
}
```

Показывать **999 ₽ / месяц** и **8990 ₽ / год**.  
В `checkout` уходит `plan_id` (= `id` из списка), не цена.

Текущая подписка (бейдж PRO):

`GET /me/subscription?audience=pro_trainer` или `pro_client`

- `data: null` — нет подписки  
- `data.status === "active"` — PRO есть, `ends_at` — до какой даты

---

## 3. Checkout

`POST /me/subscription/checkout`

```json
{ "plan_id": 3 }
```

Ответ (живой Robokassa):

```json
{
  "success": true,
  "data": {
    "subscription_id": null,
    "payment_id": 17,
    "inv_id": 17,
    "payment_url": "https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=TrainHub&OutSum=999.00&InvId=17&…",
    "provider": "robokassa",
    "status": "pending",
    "is_test": false,
    "amount": "999.00",
    "currency": "RUB",
    "plan_id": 3,
    "ends_at": null
  }
}
```

Сохранить `payment_id` / `inv_id`.  
Сразу открыть **`data.payment_url`** (не собирать URL самим).

Если `provider === "mock"` — это только локальная среда без ключей, PRO уже `active`. На проде так не будет.

`PATCH /me/subscription` с `plan_id` — тот же checkout (новый платёж). Смену тарифа делать через обычный checkout.

---

## 4. WebView

Открыть `payment_url` in-app (не внешний Safari/Chrome, если можно оставить пользователя в приложении).

Ловить переход на наши страницы:

| URL | Смысл | UI |
|-----|--------|----|
| `http://51.20.92.246/pay/success` | клиент закончил оплату у Robokassa | «Платёж отправлен, проверяем…» |
| `http://51.20.92.246/pay/fail` | отмена / ошибка карты | «Оплата не прошла» + кнопка повторить |

Детект: `url.contains("/pay/success")` / `url.contains("/pay/fail")` — затем **закрыть WebView**.

Эти страницы **не** включают PRO. Не парсить HTML. Не читать query `InvId` как факт оплаты.

### Flutter

```dart
WebViewController()
  ..setNavigationDelegate(NavigationDelegate(
    onNavigationRequest: (req) {
      final url = req.url;
      if (url.contains('/pay/success')) {
        onPayReturned(success: true);
        return NavigationDecision.prevent;
      }
      if (url.contains('/pay/fail')) {
        onPayReturned(success: false);
        return NavigationDecision.prevent;
      }
      return NavigationDecision.navigate;
    },
  ))
  ..loadRequest(Uri.parse(paymentUrl));
```

### React Native

```jsx
<WebView
  source={{ uri: paymentUrl }}
  onNavigationStateChange={(nav) => {
    if (nav.url.includes('/pay/success')) onPayReturned({ ok: true });
    if (nav.url.includes('/pay/fail')) onPayReturned({ ok: false });
  }}
/>
```

Android: `http://` без SSL — `android:usesCleartextTraffic="true"` (или network security config) для `51.20.92.246`, иначе WebView может не открыть success/fail.

---

## 5. После WebView — polling

Success-страница ≠ PRO. Опрашивать 1–2 сек, до ~90 сек.

**Вариант A (экран PRO):**

`GET /me/subscription?audience=pro_trainer` или `pro_client`

Готово, когда `data != null` и `data.status === "active"`.

**Вариант B (этот платёж):**

`GET /payments/{payment_id}`

Готово, когда `data.status === "paid"`.

Пока `pending` — лоадер «Подтверждаем оплату».  
Таймаут — «Оплата обрабатывается, PRO появится через минуту. Обновите экран.»  
Fail WebView — **не** ждать PRO, показать ошибку.

Повторить незавершённый:

`POST /payments/{payment_id}/retry` — для `pending` и `failed`.  
В ответе новый `payment_url` — снова открыть WebView. Старый `payment_id` больше не использовать.

---

## 6. Остальные billing-методы

| Метод | Зачем |
|-------|--------|
| `GET /payments` | история: `status` = `pending` \| `paid` \| `failed` \| `refunded` |
| `GET /payments/{id}` | чек |
| `POST /me/subscription/cancel` | тело нет; PRO до `ends_at` |
| `POST /me/subscription/resume` | тело нет |
| `PATCH /me/subscription` | `{ "auto_renew": false }` без `plan_id` — как cancel |

`/me/payment-methods` — **mock карточки**, к Robokassa не относятся. Для живой оплаты не использовать.

Webhook с приложения **не вызывать**.

---

## 7. Состояния экрана

| Состояние | Как понять | UI |
|-----------|------------|----|
| Нет PRO | subscription `null` или не `active` | тарифы + «Оплатить» |
| Идёт оплата | checkout ок, WebView открыт | Robokassa |
| Ждём банк | вернулись с `/pay/success`, подписка ещё не `active` | лоадер |
| PRO | `status === "active"` | период, `ends_at`, отмена автопродления |
| Не оплатил | `/pay/fail` или retry | ошибка + «Повторить» |

Лимит 5 клиентов у Coach без PRO: `403 TRAINER_PRO_REQUIRED` — вести на этот же checkout.

---

## 8. Чего не делать

- Не класть MerchantLogin / пароли в приложение  
- Не подписывать MD5 на клиенте  
- Не считать `/pay/success` активацией  
- Не открывать `https://auth.robokassa.ru/...` руками без `payment_url` из checkout  
- Не слать Result URL с телефона
