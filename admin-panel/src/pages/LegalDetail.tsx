import { FormEvent, useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Badge, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { initials } from "../lib/format";
import { LEGAL_LABELS } from "../lib/options";

const LEGAL_EXTS = [".pdf", ".doc", ".docx"];

function legalExtOk(name: string) {
  const lower = name.toLowerCase();
  return LEGAL_EXTS.some((ext) => lower.endsWith(ext));
}

export function LegalDetailPage() {
  const { docType = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"text" | "file">("text");
  const [body, setBody] = useState("");
  const [version, setVersion] = useState("1.0");
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [error, setError] = useState("");
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-legal", docType],
    queryFn: () => adminApi.legal(docType),
    enabled: docType === "terms" || docType === "privacy",
  });

  useEffect(() => {
    if (data) {
      setBody(String(data.body_md ?? ""));
      setVersion(String(data.version ?? "1.0"));
      const url = String(data.file_url ?? "");
      const name = String(data.file_name ?? "");
      setFileUrl(url);
      setFileName(name);
      setFile(null);
      setMode(url ? "file" : "text");
    }
  }, [data]);

  if (docType !== "terms" && docType !== "privacy") {
    return <Navigate to="/legal" replace />;
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      if (mode === "file") {
        if (file && !legalExtOk(file.name)) {
          setError("Разрешены только файлы PDF, DOC и DOCX");
          return;
        }
        if (!file && !fileUrl) {
          setError("Загрузите файл PDF, DOC или DOCX");
          return;
        }
        await adminApi.uploadLegalFile(docType, version, file ?? undefined);
      } else {
        if (!body.trim()) {
          setError("Введите текст документа");
          return;
        }
        await adminApi.updateLegal(docType, { body_md: body, version });
      }
      await queryClient.invalidateQueries({ queryKey: ["admin-legal"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-legal-list"] });
      navigate("/legal", { state: { success: "Документ сохранён" } });
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить документ"));
    }
  }

  const title = LEGAL_LABELS[docType] ?? "Документ";

  return (
    <DetailLayout
      backTo="/legal"
      title={title}
      subtitle={data ? `версия ${String(data.version ?? "1.0")}` : undefined}
      avatar={initials(title)}
      badges={
        data ? (
          data.file_url ? <Badge tone="lime">файл</Badge> : <Badge tone="blue">текст</Badge>
        ) : null
      }
    >
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить документ") : "")} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <Section title="Редактор">
          <form className="stack-form" onSubmit={(e) => void onSave(e)}>
            <label>
              Версия
              <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="1.0" />
            </label>
            <div>
              <p className="field-label">Содержимое</p>
              <div className="chip-group">
                <button
                  type="button"
                  className={`chip${mode === "text" ? " is-active" : ""}`}
                  onClick={() => setMode("text")}
                >
                  Текст
                </button>
                <button
                  type="button"
                  className={`chip${mode === "file" ? " is-active" : ""}`}
                  onClick={() => setMode("file")}
                >
                  Файл
                </button>
              </div>
              <p className="hint">Можно сохранить либо текст, либо файл. PDF, DOC или DOCX.</p>
            </div>
            {mode === "text" ? (
              <label>
                Текст
                <textarea rows={16} value={body} onChange={(e) => setBody(e.target.value)} />
              </label>
            ) : (
              <div className="file-picker">
                {fileUrl ? (
                  <p className="file-current">
                    Текущий файл:{" "}
                    <a className="file-link" href={fileUrl} target="_blank" rel="noreferrer">
                      {fileName || "открыть"}
                    </a>
                  </p>
                ) : (
                  <p className="muted">Файл ещё не загружен</p>
                )}
                <div className="file-control">
                  <input
                    id="legal-file"
                    className="file-control-input"
                    type="file"
                    accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(e) => {
                      const next = e.target.files?.[0] ?? null;
                      if (next && !legalExtOk(next.name)) {
                        setFile(null);
                        setError("Разрешены только файлы PDF, DOC и DOCX");
                        e.target.value = "";
                        return;
                      }
                      setError("");
                      setFile(next);
                    }}
                  />
                  <label htmlFor="legal-file" className="file-control-btn">
                    {file || fileUrl ? "Заменить файл" : "Выбрать файл"}
                  </label>
                  <span className="file-control-name">
                    {file ? file.name : fileName || "Файл не выбран"}
                  </span>
                </div>
              </div>
            )}
            <div className="modal-actions">
              <button type="submit">Сохранить</button>
            </div>
          </form>
        </Section>
      ) : null}
    </DetailLayout>
  );
}
