import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { adminApi } from "../api/resources";
import { DataTable, Toolbar } from "../components/DataTable";
import { IconBlock, IconBtn, IconOpen, IconUnlock } from "../components/IconBtn";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, EntityCell } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { initials, labelOf, personName } from "../lib/format";
import { ROLE_LABELS, ROLE_OPTIONS } from "../lib/options";

export function UsersPage() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-users", q, role],
    queryFn: () => adminApi.users({ q, role, page: 1, page_size: 50 }),
  });

  async function toggleBlock(row: Record<string, unknown>) {
    setError("");
    setSuccess("");
    try {
      const blocked = Boolean(row.is_blocked);
      await adminApi.blockUser(Number(row.id), !blocked, blocked ? undefined : "Заблокирован администратором");
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setSuccess(blocked ? "Пользователь разблокирован" : "Пользователь заблокирован");
    } catch (err) {
      setError(apiError(err, "Не удалось изменить статус пользователя"));
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>Пользователи</h1>
      </div>
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить пользователей") : "")} success={success} />
      <Toolbar>
        <input placeholder="Поиск" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select
          value={role}
          onChange={setRole}
          options={ROLE_OPTIONS}
          allowEmpty
          emptyLabel="Все роли"
          placeholder="Роль"
        />
      </Toolbar>
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      <DataTable
        rows={data?.items ?? []}
        empty={q ? "Ничего не найдено" : "Пока нет пользователей"}
        emptyHint={q ? "Попробуйте изменить запрос или роль." : undefined}
        columns={[
          { key: "id", label: "ID" },
          {
            key: "name",
            label: "Пользователь",
            render: (row) => (
              <EntityCell
                avatar={initials(row.first_name, row.last_name)}
                title={personName(row.first_name, row.last_name)}
                subtitle={String(row.email ?? row.public_id ?? "—")}
              />
            ),
          },
          {
            key: "roles",
            label: "Роли",
            render: (row) =>
              Array.isArray(row.roles) ? (
                <div className="badge-row">
                  {row.roles.map((item) => (
                    <Badge key={String(item)} tone={String(item) === "admin" ? "lime" : "blue"}>
                      {labelOf(ROLE_LABELS, item)}
                    </Badge>
                  ))}
                </div>
              ) : (
                "—"
              ),
          },
          {
            key: "is_blocked",
            label: "Статус",
            render: (row) =>
              row.is_blocked ? <Badge tone="red">заблокирован</Badge> : <Badge tone="lime">активен</Badge>,
          },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <div className="row-actions">
                <IconBtn to={`/users/${row.id}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
                <IconBtn
                  tone={row.is_blocked ? "lime" : "red"}
                  title={row.is_blocked ? "Разблокировать" : "Заблокировать"}
                  onClick={() => void toggleBlock(row)}
                >
                  {row.is_blocked ? <IconUnlock /> : <IconBlock />}
                </IconBtn>
              </div>
            ),
          },
        ]}
      />
      <p className="muted">{data ? `Всего: ${data.total}` : ""}</p>
    </div>
  );
}
