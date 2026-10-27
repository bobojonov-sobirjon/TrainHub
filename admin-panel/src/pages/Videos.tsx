import { FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DataTable } from "../components/DataTable";
import { IconArchive, IconBtn, IconOpen } from "../components/IconBtn";
import { FileField, ImageField } from "../components/MediaFields";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { initials } from "../lib/format";
import { toInt } from "../lib/numbers";

const STATUS_OPTIONS = [
  { value: "", label: "Все статусы" },
  { value: "pending_review", label: "На модерации" },
  { value: "published", label: "Опубликовано" },
  { value: "draft", label: "Черновик" },
  { value: "rejected", label: "Отклонено" },
  { value: "archived", label: "Архив" },
];

const LEVEL_OPTIONS = [
  { value: "beginner", label: "Начальный" },
  { value: "intermediate", label: "Средний" },
  { value: "advanced", label: "Продвинутый" },
];

const emptyVideo = {
  title: "",
  description: "",
  categoryId: "",
  topicId: "",
  level: "beginner",
  durationSeconds: "",
  publish: true,
  video: null as File | null,
  thumbnail: [] as File[],
};

export function VideosPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const categoryId = params.get("category_id") ?? "";
  const search = params.get("search") ?? "";

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyVideo);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();

  const categoriesQuery = useQuery({
    queryKey: ["admin-video-categories"],
    queryFn: adminApi.videoCategories,
  });
  const topicsQuery = useQuery({
    queryKey: ["admin-category-topics", form.categoryId],
    queryFn: () => adminApi.categoryTopics(Number(form.categoryId)),
    enabled: Boolean(form.categoryId),
  });
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-videos", status, categoryId, search],
    queryFn: () =>
      adminApi.videos({
        status: status || undefined,
        category_id: categoryId || undefined,
        search: search || undefined,
        page: 1,
        page_size: 50,
      }),
  });

  const categoryOptions = useMemo(
    () =>
      (categoriesQuery.data ?? [])
        .filter((row) => row.is_active !== false)
        .map((row) => ({ value: String(row.id), label: String(row.name ?? row.id) })),
    [categoriesQuery.data],
  );

  const topicOptions = useMemo(
    () =>
      (topicsQuery.data ?? [])
        .filter((row) => row.is_active !== false)
        .map((row) => ({ value: String(row.id), label: String(row.name ?? row.id) })),
    [topicsQuery.data],
  );

  function closeModal() {
    setOpen(false);
    setForm(emptyVideo);
    setSaving(false);
    setError("");
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const payload = new FormData();
      payload.append("title", form.title.trim());
      payload.append("category_id", form.categoryId);
      payload.append("topic_id", form.topicId);
      if (form.description.trim()) payload.append("description", form.description.trim());
      payload.append("level", form.level);
      const duration = toInt(form.durationSeconds);
      if (duration != null) payload.append("duration_seconds", String(duration));
      payload.append("publish", form.publish ? "true" : "false");
      if (form.video) payload.append("video", form.video);
      if (form.thumbnail[0]) payload.append("thumbnail", form.thumbnail[0]);
      await adminApi.createVideo(payload);
      closeModal();
      await queryClient.invalidateQueries({ queryKey: ["admin-videos"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-video-categories"] });
      setSuccess("Видеоурок создан");
    } catch (err) {
      setError(apiError(err, "Не удалось создать видеоурок"));
      setSaving(false);
    }
  }

  async function onArchive(id: number) {
    setError("");
    setSuccess("");
    try {
      await adminApi.archiveVideo(id);
      await queryClient.invalidateQueries({ queryKey: ["admin-videos"] });
      setSuccess("Видео архивировано");
    } catch (err) {
      setError(apiError(err, "Не удалось архивировать"));
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>Видеоуроки</h1>
        <button
          type="button"
          onClick={() => {
            setError("");
            setForm({
              ...emptyVideo,
              categoryId: categoryId || categoryOptions[0]?.value || "",
            });
            setOpen(true);
          }}
        >
          Создать
        </button>
      </div>

      <div className="filters-row" style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <Select
          value={status}
          onChange={(value) => {
            const next = new URLSearchParams(params);
            if (value) next.set("status", value);
            else next.delete("status");
            setParams(next);
          }}
          options={STATUS_OPTIONS}
        />
        <Select
          value={categoryId}
          onChange={(value) => {
            const next = new URLSearchParams(params);
            if (value) next.set("category_id", value);
            else next.delete("category_id");
            setParams(next);
          }}
          options={[{ value: "", label: "Все категории" }, ...categoryOptions]}
        />
        <input
          placeholder="Поиск…"
          value={search}
          onChange={(e) => {
            const next = new URLSearchParams(params);
            if (e.target.value) next.set("search", e.target.value);
            else next.delete("search");
            setParams(next);
          }}
          style={{ minWidth: 200 }}
        />
        <Link to="/videos?status=pending_review">
          <button type="button" className="ghost">
            Очередь модерации
          </button>
        </Link>
      </div>

      <Notice
        error={open ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить видео") : "")}
        success={success}
      />

      <DataTable
        rows={data?.items ?? []}
        empty={isLoading ? "Загрузка…" : "Видеоуроков пока нет"}
        emptyHint="Создайте категорию и тему, затем добавьте ролик"
        columns={[
          { key: "n", label: "№" },
          {
            key: "title",
            label: "Урок",
            render: (row) => (
              <EntityCell
                avatar={initials(row.title)}
                title={String(row.title ?? "—")}
                subtitle={`${row.category_name ?? "—"} · ${row.topic_name ?? "—"}`}
              />
            ),
          },
          {
            key: "source_type",
            label: "Источник",
            render: (row) => (
              <Badge tone={row.source_type === "trainer" ? "blue" : "lime"}>
                {row.source_type === "trainer" ? "Тренер" : "Админ"}
              </Badge>
            ),
          },
          {
            key: "status",
            label: "Статус",
            render: (row) => <Badge tone="muted">{String(row.status ?? "—")}</Badge>,
          },
          {
            key: "actions",
            label: "",
            render: (row) => {
              const id = Number(row.id);
              return (
                <div className="row-actions">
                  <Link to={`/videos/${id}`}>
                    <IconBtn title="Открыть">
                      <IconOpen />
                    </IconBtn>
                  </Link>
                  {row.status !== "archived" ? (
                    <IconBtn title="Архив" onClick={() => void onArchive(id)}>
                      <IconArchive />
                    </IconBtn>
                  ) : null}
                </div>
              );
            },
          },
        ]}
      />

      <Modal open={open} title="Новый видеоурок" onClose={closeModal}>
        <form className="form-grid" onSubmit={(e) => void onCreate(e)}>
          <label>
            Название *
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </label>
          <label>
            Категория *
            <Select
              value={form.categoryId}
              onChange={(value) => setForm({ ...form, categoryId: value, topicId: "" })}
              options={[{ value: "", label: "Выберите" }, ...categoryOptions]}
            />
          </label>
          <label>
            Тема *
            <Select
              value={form.topicId}
              onChange={(value) => setForm({ ...form, topicId: value })}
              options={[{ value: "", label: form.categoryId ? "Выберите тему" : "Сначала категория" }, ...topicOptions]}
            />
          </label>
          <label>
            Описание
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
            />
          </label>
          <label>
            Уровень
            <Select
              value={form.level}
              onChange={(value) => setForm({ ...form, level: value })}
              options={LEVEL_OPTIONS}
            />
          </label>
          <label>
            Длительность (сек)
            <input
              value={form.durationSeconds}
              onChange={(e) => setForm({ ...form, durationSeconds: e.target.value })}
              inputMode="numeric"
            />
          </label>
          <ImageField
            id="video-thumb"
            label="Обложка"
            multiple={false}
            files={form.thumbnail}
            onFiles={(files) => setForm({ ...form, thumbnail: files.slice(0, 1) })}
          />
          <FileField
            id="video-file"
            label="Видеофайл"
            file={form.video}
            onFile={(file) => setForm({ ...form, video: file })}
          />
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.publish}
              onChange={(e) => setForm({ ...form, publish: e.target.checked })}
            />
            Сразу опубликовать в каталоге
          </label>
          <Notice error={error} />
          <div className="modal-actions">
            <button type="button" className="ghost" onClick={closeModal}>
              Отмена
            </button>
            <button type="submit" disabled={saving || !form.categoryId || !form.topicId}>
              {saving ? "Создание…" : "Создать"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
