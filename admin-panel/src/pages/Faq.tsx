import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DataTable } from "../components/DataTable";
import { IconBtn, IconEye, IconEyeOff, IconOpen } from "../components/IconBtn";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { initials } from "../lib/format";
import { toInt } from "../lib/numbers";
import { FAQ_AUDIENCE_LABELS, FAQ_AUDIENCE_OPTIONS } from "../lib/options";

const emptyFaq = {
  question: "",
  answer: "",
  slug: "",
  audience: "all",
  sortOrder: "0",
  isPublished: true,
};

function makeSlug(value: string) {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 80) || `faq-${Date.now()}`
  );
}

export function FaqPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyFaq);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();
  const { data, error: loadError } = useQuery({ queryKey: ["admin-faq"], queryFn: adminApi.faq });

  function closeModal() {
    setOpen(false);
    setForm(emptyFaq);
    setSaving(false);
    setError("");
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await adminApi.createFaq({
        slug: form.slug.trim() || makeSlug(form.question),
        question: form.question.trim(),
        answer: form.answer.trim(),
        audience: form.audience,
        sort_order: toInt(form.sortOrder) ?? 0,
        is_published: form.isPublished,
      });
      closeModal();
      await queryClient.invalidateQueries({ queryKey: ["admin-faq"] });
      setSuccess("Статья FAQ добавлена");
    } catch (err) {
      setError(apiError(err, "Не удалось добавить статью"));
      setSaving(false);
    }
  }

  async function onPublish(id: number, isPublished: boolean) {
    setError("");
    setSuccess("");
    try {
      await adminApi.publishFaq(id, !isPublished);
      await queryClient.invalidateQueries({ queryKey: ["admin-faq"] });
      setSuccess(isPublished ? "Статья скрыта" : "Статья опубликована");
    } catch (err) {
      setError(apiError(err, "Не удалось изменить публикацию"));
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>FAQ</h1>
        <button
          type="button"
          onClick={() => {
            setError("");
            setOpen(true);
          }}
        >
          Создать
        </button>
      </div>
      <Notice error={open ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить FAQ") : "")} success={success} />
      <DataTable
        rows={data ?? []}
        columns={[
          { key: "id", label: "ID" },
          {
            key: "question",
            label: "Статья",
            render: (row) => (
              <EntityCell
                avatar={initials(row.question)}
                title={String(row.question ?? "—")}
                subtitle={String(row.slug ?? "")}
              />
            ),
          },
          {
            key: "audience",
            label: "Аудитория",
            render: (row) => <Badge tone="blue">{FAQ_AUDIENCE_LABELS[String(row.audience)] ?? String(row.audience ?? "—")}</Badge>,
          },
          {
            key: "is_published",
            label: "Статус",
            render: (row) => (row.is_published ? <Badge tone="lime">опубликовано</Badge> : <Badge>скрыто</Badge>),
          },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <div className="row-actions">
                <IconBtn to={`/faq/${row.id}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
                <IconBtn
                  tone={row.is_published ? "muted" : "lime"}
                  title={row.is_published ? "Скрыть" : "Опубликовать"}
                  onClick={() => void onPublish(Number(row.id), Boolean(row.is_published))}
                >
                  {row.is_published ? <IconEyeOff /> : <IconEye />}
                </IconBtn>
              </div>
            ),
          },
        ]}
      />
      <Modal open={open} title="Новая статья FAQ" onClose={closeModal}>
        <Notice error={error} />
        <form className="stack-form" onSubmit={(e) => void onCreate(e)}>
          <label>
            Вопрос
            <input
              value={form.question}
              onChange={(e) => setForm((current) => ({ ...current, question: e.target.value }))}
              required
            />
          </label>
          <label>
            Ответ
            <textarea
              rows={8}
              value={form.answer}
              onChange={(e) => setForm((current) => ({ ...current, answer: e.target.value }))}
              required
            />
          </label>
          <div className="form-grid">
            <label>
              Аудитория
              <Select
                value={form.audience}
                onChange={(audience) => setForm((current) => ({ ...current, audience }))}
                options={FAQ_AUDIENCE_OPTIONS}
              />
            </label>
            <label>
              Порядок
              <input
                type="number"
                min={0}
                value={form.sortOrder}
                onChange={(e) => setForm((current) => ({ ...current, sortOrder: e.target.value }))}
              />
            </label>
          </div>
          <label>
            Slug
            <input
              value={form.slug}
              onChange={(e) => setForm((current) => ({ ...current, slug: e.target.value }))}
              placeholder="оставьте пустым — создастся автоматически"
            />
          </label>
          <label className="check-row">
            <input
              type="checkbox"
              checked={form.isPublished}
              onChange={(e) => setForm((current) => ({ ...current, isPublished: e.target.checked }))}
            />
            Опубликовать сразу
          </label>
          <div className="modal-actions">
            <button type="button" className="ghost" onClick={closeModal}>
              Отмена
            </button>
            <button type="submit" disabled={saving}>
              {saving ? "Сохранение..." : "Создать"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
