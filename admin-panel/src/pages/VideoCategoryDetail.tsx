import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { DataTable } from "../components/DataTable";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Badge } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { toInt } from "../lib/numbers";

export function VideoCategoryDetailPage() {
  const { id } = useParams();
  const categoryId = Number(id);
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();
  const [saving, setSaving] = useState(false);
  const [topicOpen, setTopicOpen] = useState(false);
  const [topicName, setTopicName] = useState("");
  const [topicDesc, setTopicDesc] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sortOrder, setSortOrder] = useState("0");
  const [isActive, setIsActive] = useState(true);

  const categoriesQuery = useQuery({
    queryKey: ["admin-video-categories"],
    queryFn: adminApi.videoCategories,
  });
  const topicsQuery = useQuery({
    queryKey: ["admin-category-topics", categoryId],
    queryFn: () => adminApi.categoryTopics(categoryId),
    enabled: Number.isFinite(categoryId) && categoryId > 0,
  });
  const videosQuery = useQuery({
    queryKey: ["admin-videos-by-category", categoryId],
    queryFn: () => adminApi.videos({ category_id: categoryId, page: 1, page_size: 50 }),
    enabled: Number.isFinite(categoryId) && categoryId > 0,
  });

  const category = useMemo(
    () => (categoriesQuery.data ?? []).find((row) => Number(row.id) === categoryId),
    [categoriesQuery.data, categoryId],
  );

  useEffect(() => {
    if (!category) return;
    setName(String(category.name ?? ""));
    setDescription(String(category.description ?? ""));
    setSortOrder(String(category.sort_order ?? 0));
    setIsActive(Boolean(category.is_active));
  }, [category]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await adminApi.updateVideoCategory(categoryId, {
        name: name.trim(),
        description: description.trim() || null,
        sort_order: toInt(sortOrder) ?? 0,
        is_active: isActive,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin-video-categories"] });
      setSuccess("Категория сохранена");
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить"));
    } finally {
      setSaving(false);
    }
  }

  async function onCreateTopic(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    try {
      await adminApi.createTopic({
        category_id: categoryId,
        name: topicName.trim(),
        description: topicDesc.trim() || null,
        sort_order: topicsQuery.data?.length ?? 0,
        is_active: true,
      });
      setTopicOpen(false);
      setTopicName("");
      setTopicDesc("");
      await queryClient.invalidateQueries({ queryKey: ["admin-category-topics", categoryId] });
      await queryClient.invalidateQueries({ queryKey: ["admin-video-categories"] });
      setSuccess("Тема добавлена");
    } catch (err) {
      setError(apiError(err, "Не удалось создать тему"));
    }
  }

  if (!Number.isFinite(categoryId) || categoryId <= 0) {
    return <Notice error="Некорректный id категории" />;
  }

  return (
    <DetailLayout
      title={String(category?.name ?? `Категория #${categoryId}`)}
      backTo="/video-categories"
      backLabel="К категориям"
    >
      <Notice
        error={
          error ||
          (categoriesQuery.error ? apiError(categoriesQuery.error, "Не удалось загрузить") : "")
        }
        success={success}
      />

      <form className="form-grid card" onSubmit={(e) => void onSave(e)}>
        <h2>Параметры</h2>
        <label>
          Название
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Описание
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
        </label>
        <label>
          Порядок
          <input value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} inputMode="numeric" />
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Активна в каталоге приложения
        </label>
        <div className="modal-actions">
          <button type="submit" disabled={saving}>
            {saving ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </form>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="page-head">
          <h2>Темы</h2>
          <button type="button" onClick={() => setTopicOpen(true)}>
            Добавить тему
          </button>
        </div>
        <DataTable
          rows={topicsQuery.data ?? []}
          empty="Тем пока нет — без темы нельзя добавить видеоурок"
          columns={[
            { key: "n", label: "№" },
            { key: "name", label: "Тема" },
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
                  {row.is_active ? "Активна" : "Скрыта"}
                </Badge>
              ),
            },
          ]}
        />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="page-head">
          <h2>Видеоуроки в категории</h2>
          <Link to={`/videos?category_id=${categoryId}`}>
            <button type="button">Все видео</button>
          </Link>
        </div>
        <DataTable
          rows={videosQuery.data?.items ?? []}
          empty="Видеоуроков пока нет"
          columns={[
            { key: "n", label: "№" },
            { key: "title", label: "Название" },
            { key: "topic_name", label: "Тема" },
            {
              key: "status",
              label: "Статус",
              render: (row) => <Badge tone="blue">{String(row.status ?? "—")}</Badge>,
            },
            {
              key: "actions",
              label: "",
              render: (row) => <Link to={`/videos/${Number(row.id)}`}>Открыть</Link>,
            },
          ]}
        />
      </div>

      <Modal open={topicOpen} title="Новая тема" onClose={() => setTopicOpen(false)}>
        <form className="form-grid" onSubmit={(e) => void onCreateTopic(e)}>
          <label>
            Название *
            <input required value={topicName} onChange={(e) => setTopicName(e.target.value)} />
          </label>
          <label>
            Описание
            <textarea value={topicDesc} onChange={(e) => setTopicDesc(e.target.value)} rows={3} />
          </label>
          <div className="modal-actions">
            <button type="button" className="ghost" onClick={() => setTopicOpen(false)}>
              Отмена
            </button>
            <button type="submit">Создать</button>
          </div>
        </form>
      </Modal>
    </DetailLayout>
  );
}
