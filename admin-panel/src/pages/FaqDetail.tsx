import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { initials, labelOf } from "../lib/format";
import { toInt } from "../lib/numbers";
import { FAQ_AUDIENCE_LABELS, FAQ_AUDIENCE_OPTIONS } from "../lib/options";

export function FaqDetailPage() {
  const { id } = useParams();
  const faqId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [audience, setAudience] = useState("all");
  const [slug, setSlug] = useState("");
  const [sortOrder, setSortOrder] = useState("0");
  const [isPublished, setIsPublished] = useState(true);
  const [error, setError] = useState("");
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-faq-item", faqId],
    queryFn: () => adminApi.faqItem(faqId),
    enabled: Number.isFinite(faqId),
  });

  useEffect(() => {
    if (!data) return;
    setQuestion(String(data.question ?? ""));
    setAnswer(String(data.answer ?? ""));
    setAudience(String(data.audience ?? "all"));
    setSlug(String(data.slug ?? ""));
    setSortOrder(String(data.sort_order ?? 0));
    setIsPublished(Boolean(data.is_published));
  }, [data]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!data) return;
    setError("");
    try {
      await adminApi.updateFaq(faqId, {
        slug: slug.trim() || String(data.slug),
        question,
        answer,
        audience,
        sort_order: toInt(sortOrder) ?? 0,
        is_published: isPublished,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin-faq"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-faq-item", faqId] });
      navigate("/faq", { state: { success: "Статья сохранена" } });
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить статью"));
    }
  }

  return (
    <DetailLayout
      backTo="/faq"
      title={data ? String(data.question) : "FAQ"}
      subtitle={data ? String(data.slug) : undefined}
      avatar={data ? initials(data.question) : "F"}
      badges={
        data ? (
          <>
            <Badge tone="blue">{labelOf(FAQ_AUDIENCE_LABELS, data.audience)}</Badge>
            {data.is_published ? <Badge tone="lime">опубликовано</Badge> : <Badge>скрыто</Badge>}
          </>
        ) : null
      }
    >
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить статью") : "")} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <Section title="Статья">
          <form className="stack-form" onSubmit={(e) => void onSave(e)}>
            <label>
              Вопрос
              <input value={question} onChange={(e) => setQuestion(e.target.value)} required />
            </label>
            <label>
              Ответ
              <textarea rows={10} value={answer} onChange={(e) => setAnswer(e.target.value)} required />
            </label>
            <div className="form-grid">
              <label>
                Аудитория
                <Select value={audience} onChange={setAudience} options={FAQ_AUDIENCE_OPTIONS} />
              </label>
              <label>
                Порядок
                <input type="number" min={0} value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} />
              </label>
            </div>
            <label>
              Slug
              <input value={slug} onChange={(e) => setSlug(e.target.value)} required />
            </label>
            <label className="check-row">
              <input type="checkbox" checked={isPublished} onChange={(e) => setIsPublished(e.target.checked)} />
              Опубликовано
            </label>
            <div className="modal-actions">
              <button type="submit">Сохранить</button>
            </div>
          </form>
        </Section>
      ) : null}
    </DetailLayout>
  );
}
