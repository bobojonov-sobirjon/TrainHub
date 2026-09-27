import { useMemo } from "react";

const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif";
const VIDEO_ACCEPT = "video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm";

function fileNameFromUrl(url: string) {
  try {
    return decodeURIComponent(url.split("/").pop() || "файл");
  } catch {
    return "файл";
  }
}

export function ImageField({
  id,
  label = "Фото",
  hint = "Можно выбрать несколько изображений: JPG, PNG, WEBP, GIF.",
  multiple = true,
  existing = [],
  files,
  onFiles,
  onRemoveExisting,
}: {
  id: string;
  label?: string;
  hint?: string;
  multiple?: boolean;
  existing?: string[];
  files: File[];
  onFiles: (files: File[]) => void;
  onRemoveExisting?: (url: string) => void;
}) {
  const previews = useMemo(() => files.map((file) => ({ file, url: URL.createObjectURL(file) })), [files]);

  return (
    <div className="file-picker">
      <p className="field-label">{label}</p>
      {existing.length || previews.length ? (
        <div className="media-grid">
          {existing.map((url) => (
            <figure key={url} className="media-thumb">
              <img src={url} alt="" />
              {onRemoveExisting ? (
                <button type="button" className="media-remove" onClick={() => onRemoveExisting(url)}>
                  ×
                </button>
              ) : null}
            </figure>
          ))}
          {previews.map(({ file, url }) => (
            <figure key={file.name + file.size} className="media-thumb">
              <img src={url} alt={file.name} />
              <button
                type="button"
                className="media-remove"
                onClick={() => onFiles(files.filter((item) => item !== file))}
              >
                ×
              </button>
            </figure>
          ))}
        </div>
      ) : (
        <p className="muted">Фото ещё не загружены</p>
      )}
      <div className="file-control">
        <input
          id={id}
          className="file-control-input"
          type="file"
          accept={IMAGE_ACCEPT}
          multiple={multiple}
          onChange={(event) => {
            const next = Array.from(event.target.files ?? []);
            onFiles(multiple ? [...files, ...next] : next.slice(0, 1));
            event.target.value = "";
          }}
        />
        <label htmlFor={id} className="file-control-btn">
          {existing.length || files.length ? "Добавить фото" : "Выбрать фото"}
        </label>
        <span className="file-control-name">
          {files.length ? `${files.length} файл(ов)` : "Файл не выбран"}
        </span>
      </div>
      <p className="hint">{hint}</p>
    </div>
  );
}

export function FileField({
  id,
  label = "Видео",
  hint = "Один файл: MP4, MOV или WEBM.",
  accept = VIDEO_ACCEPT,
  existingUrl,
  file,
  onFile,
  onClear,
}: {
  id: string;
  label?: string;
  hint?: string;
  accept?: string;
  existingUrl?: string | null;
  file: File | null;
  onFile: (file: File | null) => void;
  onClear?: () => void;
}) {
  return (
    <div className="file-picker">
      <p className="field-label">{label}</p>
      {file ? (
        <p className="file-current">{file.name}</p>
      ) : existingUrl ? (
        <p className="file-current">
          Текущий файл:{" "}
          <a className="file-link" href={existingUrl} target="_blank" rel="noreferrer">
            {fileNameFromUrl(existingUrl)}
          </a>
        </p>
      ) : (
        <p className="muted">Файл ещё не загружен</p>
      )}
      <div className="file-control">
        <input
          id={id}
          className="file-control-input"
          type="file"
          accept={accept}
          onChange={(event) => {
            onFile(event.target.files?.[0] ?? null);
            event.target.value = "";
          }}
        />
        <label htmlFor={id} className="file-control-btn">
          {file || existingUrl ? "Заменить файл" : "Выбрать файл"}
        </label>
        <span className="file-control-name">{file ? file.name : existingUrl ? fileNameFromUrl(existingUrl) : "Файл не выбран"}</span>
        {file || existingUrl ? (
          <button
            type="button"
            className="ghost"
            onClick={() => {
              onFile(null);
              onClear?.();
            }}
          >
            Удалить
          </button>
        ) : null}
      </div>
      <p className="hint">{hint}</p>
    </div>
  );
}
