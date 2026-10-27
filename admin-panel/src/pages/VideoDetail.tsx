import { FormEvent, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Badge } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";

export function VideoDetailPage() {
  const { id } = useParams();
  const videoId = Number(id);
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const { success, setSuccess } = useFlashSuccess();

  const videoQuery = useQuery({
    queryKey: ["admin-video", videoId],
    queryFn: () => adminApi.video(videoId),
    enabled: Number.isFinite(videoId) && videoId > 0,
  });
  const assignmentsQuery = useQuery({
    queryKey: ["admin-video-assignments", videoId],
    queryFn: () => adminApi.videoAssignments(videoId),
    enabled: Number.isFinite(videoId) && videoId > 0,
  });

  const video = videoQuery.data;

  async function run(action: () => Promise<unknown>, ok: string) {
    setError("");
    setSuccess("");
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["admin-video", videoId] });
      await queryClient.invalidateQueries({ queryKey: ["admin-videos"] });
      setSuccess(ok);
    } catch (err) {
      setError(apiError(err, "Операция не удалась"));
    }
  }

  async function onReject(event: FormEvent) {
    event.preventDefault();
    if (rejectReason.trim().length < 3) {
      setError("Укажите причину (мин. 3 символа)");
      return;
    }
    await run(() => adminApi.rejectVideo(videoId, rejectReason.trim()), "Видео отклонено");
    setRejectReason("");
  }

  if (!Number.isFinite(videoId) || videoId <= 0) {
    return <Notice error="Некорректный id видео" />;
  }

  return (
    <DetailLayout
      title={String(video?.title ?? `Видео #${videoId}`)}
      backTo="/videos"
      backLabel="К видеоурокам"
    >
      <Notice
        error={error || (videoQuery.error ? apiError(videoQuery.error, "Не удалось загрузить") : "")}
        success={success}
      />

      {video ? (
        <div className="card form-grid">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge tone="muted">{String(video.status ?? "—")}</Badge>
            <Badge tone={video.source_type === "trainer" ? "blue" : "lime"}>
              {video.source_type === "trainer" ? "Тренер" : "Админ"}
            </Badge>
          </div>
          <p>
            <strong>Категория:</strong> {String(video.category_name ?? video.category_id ?? "—")}
          </p>
          <p>
            <strong>Тема:</strong> {String(video.topic_name ?? video.topic_id ?? "—")}
          </p>
          <p>
            <strong>Уровень:</strong> {String(video.level ?? "—")}
          </p>
          <p>{String(video.description ?? "")}</p>
          {video.thumbnail_url ? (
            <img
              src={String(video.thumbnail_url)}
              alt=""
              style={{ maxWidth: 320, borderRadius: 12 }}
            />
          ) : null}
          {video.video_url ? (
            <video src={String(video.video_url)} controls style={{ maxWidth: "100%", borderRadius: 12 }} />
          ) : (
            <p className="muted">Файл видео недоступен</p>
          )}

          <div className="modal-actions" style={{ justifyContent: "flex-start" }}>
            {video.status === "pending_review" ? (
              <button type="button" onClick={() => void run(() => adminApi.approveVideo(videoId), "Опубликовано")}>
                Одобрить
              </button>
            ) : null}
            {video.status !== "archived" ? (
              <button
                type="button"
                className="ghost"
                onClick={() => void run(() => adminApi.archiveVideo(videoId), "В архиве")}
              >
                В архив
              </button>
            ) : null}
          </div>

          {video.status === "pending_review" ? (
            <form className="form-grid" onSubmit={(e) => void onReject(e)}>
              <label>
                Причина отклонения
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                  placeholder="Например: плохое качество звука"
                />
              </label>
              <button type="submit" className="ghost">
                Отклонить
              </button>
            </form>
          ) : null}
        </div>
      ) : (
        <p>Загрузка…</p>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Назначения клиентам</h2>
        <ul>
          {(assignmentsQuery.data ?? []).length === 0 ? (
            <li>Назначений нет</li>
          ) : (
            (assignmentsQuery.data ?? []).map((row) => (
              <li key={String(row.id)}>
                #{String(row.id)} · client {String(row.client_id ?? "—")} · {String(row.status ?? "")}
              </li>
            ))
          )}
        </ul>
      </div>
    </DetailLayout>
  );
}
