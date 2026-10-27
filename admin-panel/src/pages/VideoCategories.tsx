import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DataTable } from "../components/DataTable";
import { IconArchive, IconBtn, IconOpen } from "../components/IconBtn";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Badge, EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { initials } from "../lib/format";
import { toInt } from "../lib/numbers";

const emptyCategory = {
  name: "",
  description: "",
  thumbnailUrl: "",
  sortOrder: "0",
  isActive: true,
  defaultTopic: "Общие",
};

export function VideoCategoriesPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyCategory);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-video-categories"],
    queryFn: adminApi.videoCategories,
  });

  function closeModal() {
    setOpen(false);
    setForm(emptyCategory);
    setSaving(false);
    setError("");
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const created = await adminApi.createVideoCategory({
        name: form.name.trim(),
        description: form.description.trim() || null,
        thumbnail_url: form.thumbnailUrl.trim() || null,
        sort_order: toInt(form.sortOrder) ?? 0,
        is_active: form.isActive,
      });
      const id = Number((created.data as { data?: { id?: number } })?.data?.id);
      if (id && form.defaultTopic.trim()) {
        await adminApi.createTopic({
          category_id: id,
          name: form.defaultTopic.trim(),
          sort_order: 0,
          is_active: true,
        });
      }
      closeModal();
      await queryClient.invalidateQueries({ queryKey: ["admin-video-categories"] });
      setSuccess("Категория создана");
    } catch (err) {
      setError(apiError(err, "Не удалось создать категорию"));
      setSaving(false);
    }
  }

  async function onArchive(id: number) {
    setError("");
    setSuccess("");
    try {
      await adminApi.archiveVideoCategory(id);
      await queryClient.invalidateQueries({ queryKey: ["admin-video-categories"] });
      setSuccess("Категория архивирована");
    } catch (err) {
      setError(apiError(err, "Не удалось архивировать категорию"));
    }
  }

  const rows = (data ?? []).map((row) => row);

  return (
    <div>
      <div className="page-head">
        <h1>Категории видео</h1>
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
      <Notice
        error={open ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить категории") : "")}
        success={success}
      />
      <DataTable
        rows={rows}
        empty={isLoading ? "Загрузка…" : "Категорий пока нет"}
        emptyHint="Создайте категорию — внутри неё темы и видеоуроки"
        columns={[
          { key: "n", label: "№" },
          {
            key: "name",
            label: "Категория",
            render: (row) => (
              <EntityCell
                avatar={initials(row.name)}
                title={String(row.name ?? "—")}
                subtitle={String(row.description ?? row.slug ?? "")}
              />
            ),
          },
          {
            key: "topics_count",
            label: "Темы",
            render: (row) => String(row.topics_count ?? 0),
          },
          {
            key: "videos_count",
            label: "Видео",
            render: (row) => String(row.videos_count ?? 0),
          },
          {
            key: "is_active",
            label: "Статус",
            render: (row) => (
              <Badge tone={row.is_active ? "lime" : "muted"}>
                {row.is_active ? "Активна" : "Архив"}
              </Badge>
            ),
          },
          {
            key: "actions",
            label: "",
            render: (row) => {
              const id = Number(row.id);
              return (
                <div className="row-actions">
                  <Link to={`/video-categories/${id}`}>
                    <IconBtn title="Открыть">
                      <IconOpen />
                    </IconBtn>
                  </Link>
                  {row.is_active ? (
                    <IconBtn title="Архивировать" onClick={() => void onArchive(id)}>
                      <IconArchive />
                    </IconBtn>
                  ) : null}
                </div>
              );
            },
          },
        ]}
      />

      <Modal open={open} title="Новая категория" onClose={closeModal}>
        <form className="form-grid" onSubmit={(e) => void onCreate(e)}>
          <label>
            Название *
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Например: Набор массы"
            />
          </label>
          <label>
            Описание
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
              placeholder="Кратко о категории"
            />
          </label>
          <label>
            Thumbnail URL
            <input
              value={form.thumbnailUrl}
              onChange={(e) => setForm({ ...form, thumbnailUrl: e.target.value })}
              placeholder="https://…"
            />
          </label>
          <label>
            Порядок
            <input
              value={form.sortOrder}
              onChange={(e) => setForm({ ...form, sortOrder: e.target.value })}
              inputMode="numeric"
            />
          </label>
          <label>
            Первая тема (для видеоуроков)
            <input
              value={form.defaultTopic}
              onChange={(e) => setForm({ ...form, defaultTopic: e.target.value })}
              placeholder="Общие"
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.isActive}
              onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
            />
            Активна в каталоге
          </label>
          <Notice error={error} />
          <div className="modal-actions">
            <button type="button" className="ghost" onClick={closeModal}>
              Отмена
            </button>
            <button type="submit" disabled={saving}>
              {saving ? "Создание…" : "Создать"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
