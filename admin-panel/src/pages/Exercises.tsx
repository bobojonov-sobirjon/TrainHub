import { FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { ChipGroup } from "../components/ChipGroup";
import { DataTable } from "../components/DataTable";
import { IconBtn, IconOpen, IconTrash } from "../components/IconBtn";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { ImageField } from "../components/MediaFields";
import { Badge } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { dash, initials } from "../lib/format";
import { useDictLabel, useDictOptions } from "../lib/options";

const emptyExercise = {
  name: "",
  muscle: "",
  equipment: "",
  kind: "strength",
  secondary: [] as string[],
  photos: [] as File[],
};

export function ExercisesPage() {
  const queryClient = useQueryClient();
  const muscles = useDictOptions("muscle_group");
  const equipmentOptions = useDictOptions("equipment");
  const kinds = useDictOptions("workout_kind");
  const muscleLabel = useDictLabel("muscle_group");
  const equipmentLabel = useDictLabel("equipment");
  const kindLabel = useDictLabel("workout_kind");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyExercise);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const { success, setSuccess } = useFlashSuccess();
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-exercises"],
    queryFn: () => adminApi.exercises({}),
  });

  const previewUrl = useMemo(
    () => (form.photos[0] ? URL.createObjectURL(form.photos[0]) : ""),
    [form.photos],
  );

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function validateCreate(values = form) {
    const next: Record<string, string> = {};
    const name = values.name.trim();
    if (!name) next.name = "Укажите название";
    else if (name.length < 2) next.name = "Минимум 2 символа";
    else if (name.length > 120) next.name = "Максимум 120 символов";
    if (!values.muscle) next.muscle = "Выберите основную мышцу";
    if (!values.kind) next.kind = "Выберите тип упражнения";
    if (!values.photos.length) next.photos = "Добавьте хотя бы одно фото";
    return next;
  }

  function patchForm(patch: Partial<typeof emptyExercise>) {
    setForm((current) => {
      const next = { ...current, ...patch };
      setFieldErrors((errors) => {
        if (!Object.keys(errors).length) return errors;
        return validateCreate(next);
      });
      return next;
    });
  }

  function openCreate() {
    setError("");
    setFieldErrors({});
    setForm(emptyExercise);
    setSaving(false);
    setOpen(true);
    void queryClient.invalidateQueries({ queryKey: ["admin-dictionaries"] });
  }

  function closeModal() {
    setOpen(false);
    setForm(emptyExercise);
    setSaving(false);
    setError("");
    setFieldErrors({});
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validateCreate();
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      setError("Заполните обязательные поля");
      return;
    }
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const payload = new FormData();
      payload.append("name", form.name.trim());
      payload.append("primary_muscle", form.muscle);
      payload.append("equipment", form.equipment);
      payload.append("exercise_type", form.kind);
      payload.append("secondary_muscles", JSON.stringify(form.secondary));
      form.photos.forEach((file) => payload.append("photos", file));
      await adminApi.createExercise(payload);
      closeModal();
      await queryClient.invalidateQueries({ queryKey: ["admin-exercises"] });
      setSuccess("Упражнение создано");
    } catch (err) {
      setError(apiError(err, "Не удалось создать упражнение"));
      setSaving(false);
    }
  }

  async function onDelete(id: number) {
    setError("");
    setSuccess("");
    try {
      await adminApi.deleteExercise(id);
      await queryClient.invalidateQueries({ queryKey: ["admin-exercises"] });
      setSuccess("Упражнение удалено");
    } catch (err) {
      setError(apiError(err, "Не удалось удалить упражнение"));
    }
  }

  return (
    <div className="list-page">
      <div className="page-head">
        <h1>Упражнения</h1>
        <button type="button" onClick={openCreate}>
          Создать
        </button>
      </div>
      <Notice error={open ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить упражнения") : "")} success={success} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      <DataTable
        rows={data ?? []}
        columns={[
          { key: "n", label: "№", className: "col-hide-xs" },
          {
            key: "name",
            label: "Упражнение",
            render: (row) => (
              <div className="entity-cell">
                {row.photo_url ? (
                  <img
                    className="entity-cell-photo"
                    src={String(row.photo_url)}
                    alt=""
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      objectFit: "contain",
                      background: "#fff",
                      flexShrink: 0,
                      padding: 4,
                    }}
                  />
                ) : (
                  <div className="entity-cell-mini">{initials(row.name)}</div>
                )}
                <div className="entity-cell-copy">
                  <strong>{dash(row.name)}</strong>
                  <span>{muscleLabel(row.primary_muscle)}</span>
                </div>
              </div>
            ),
          },
          {
            key: "equipment",
            label: "Оборудование",
            className: "col-hide-sm",
            render: (row) => <Badge tone="blue">{equipmentLabel(row.equipment)}</Badge>,
          },
          {
            key: "exercise_type",
            label: "Тип",
            className: "col-hide-sm",
            render: (row) => <Badge>{kindLabel(row.exercise_type)}</Badge>,
          },
          {
            key: "is_public",
            label: "Доступ",
            className: "col-hide-sm",
            render: (row) => (row.is_public ? <Badge tone="lime">публичное</Badge> : <Badge>личное</Badge>),
          },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <div className="row-actions">
                <IconBtn to={`/exercises/${row.id}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
                <IconBtn tone="red" title="Удалить" onClick={() => void onDelete(Number(row.id))}>
                  <IconTrash />
                </IconBtn>
              </div>
            ),
          },
        ]}
      />
      <Modal
        open={open}
        title="Новое упражнение"
        subtitle="Каталог для приложения: название, мышца и фото"
        className="exercise-create-modal"
        onClose={closeModal}
      >
        <Notice error={error} />
        <form className="stack-form exercise-create-form" onSubmit={(e) => void onCreate(e)} noValidate>
          <p className="form-rules">
            Обязательно: <strong>название</strong>, <strong>мышца</strong>, <strong>тип</strong> и{" "}
            <strong>фото</strong>. Остальное — по желанию.
          </p>

          <div className="exercise-preview">
            <div className="exercise-preview-thumb">
              {previewUrl ? <img src={previewUrl} alt="" /> : <span>{initials(form.name || "У")}</span>}
            </div>
            <div className="exercise-preview-copy">
              <strong>{form.name.trim() || "Название упражнения"}</strong>
              <span>
                {[form.muscle ? muscleLabel(form.muscle) : "Мышца", form.kind ? kindLabel(form.kind) : null]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </div>
          </div>

          <section className="form-section">
            <div className="form-section-head">
              <h3>Основное</h3>
              <p>Как упражнение будет видно в списке</p>
            </div>
            <label className={fieldErrors.name ? "has-error" : undefined}>
              <span className="field-title">
                Название <em className="req" aria-hidden>*</em>
              </span>
              <input
                value={form.name}
                onChange={(e) => patchForm({ name: e.target.value })}
                placeholder="Например: Жим лёжа"
                aria-invalid={Boolean(fieldErrors.name)}
                aria-describedby={fieldErrors.name ? "ex-name-error" : undefined}
              />
              {fieldErrors.name ? (
                <span id="ex-name-error" className="field-error">
                  {fieldErrors.name}
                </span>
              ) : null}
            </label>
            <div className="form-grid form-grid-3">
              <label className={fieldErrors.muscle ? "has-error" : undefined}>
                <span className="field-title">
                  Основная мышца <em className="req" aria-hidden>*</em>
                </span>
                <Select
                  value={form.muscle}
                  onChange={(muscle) => patchForm({ muscle })}
                  options={muscles}
                  placeholder="Выберите мышцу"
                  allowEmpty
                  emptyLabel="Выберите мышцу"
                />
                {fieldErrors.muscle ? <span className="field-error">{fieldErrors.muscle}</span> : null}
              </label>
              <label className={fieldErrors.kind ? "has-error" : undefined}>
                <span className="field-title">
                  Тип <em className="req" aria-hidden>*</em>
                </span>
                <Select
                  value={form.kind}
                  onChange={(kind) => patchForm({ kind })}
                  options={kinds}
                  placeholder="Тип"
                />
                {fieldErrors.kind ? <span className="field-error">{fieldErrors.kind}</span> : null}
              </label>
              <label>
                <span className="field-title">
                  Оборудование <span className="opt">необяз.</span>
                </span>
                <Select
                  value={form.equipment}
                  onChange={(equipment) => patchForm({ equipment })}
                  options={equipmentOptions}
                  placeholder="Оборудование"
                  allowEmpty
                  emptyLabel="Не указано"
                />
              </label>
            </div>
          </section>

          <section className="form-section">
            <div className="form-section-head">
              <h3>
                Дополнительные мышцы <span className="opt">необяз.</span>
              </h3>
              <p>Можно выбрать несколько</p>
            </div>
            <ChipGroup
              options={muscles}
              values={form.secondary}
              onChange={(secondary) => patchForm({ secondary })}
            />
          </section>

          <section className={`form-section${fieldErrors.photos ? " has-error" : ""}`}>
            <div className="form-section-head">
              <h3>
                Фото <em className="req" aria-hidden>*</em>
              </h3>
              <p>Первое фото станет превью в каталоге</p>
            </div>
            <ImageField
              id="exercise-create-photos"
              label="Изображения"
              hint="JPG, PNG или WEBP. Минимум одно фото."
              files={form.photos}
              onFiles={(photos) => patchForm({ photos })}
            />
            {fieldErrors.photos ? <span className="field-error">{fieldErrors.photos}</span> : null}
          </section>

          <div className="modal-actions">
            <button type="button" className="ghost" onClick={closeModal}>
              Отмена
            </button>
            <button type="submit" disabled={saving}>
              {saving ? "Сохранение..." : "Создать упражнение"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
