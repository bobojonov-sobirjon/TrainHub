import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { ChipGroup } from "../components/ChipGroup";
import { DataTable } from "../components/DataTable";
import { IconBtn, IconOpen, IconTrash } from "../components/IconBtn";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { FileField, ImageField } from "../components/MediaFields";
import { Badge, EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { dash, initials } from "../lib/format";
import { useDictLabel, useDictOptions } from "../lib/options";

const emptyExercise = {
  name: "",
  muscle: "chest",
  equipment: "",
  kind: "strength",
  secondary: [] as string[],
  photos: [] as File[],
  video: null as File | null,
};

export function ExercisesPage() {
  const queryClient = useQueryClient();
  const muscles = useDictOptions("muscle_group");
  const equipmentOptions = useDictOptions("equipment");
  const kinds = useDictOptions("workout_kind");
  const muscleLabel = useDictLabel("muscle_group");
  const equipmentLabel = useDictLabel("equipment");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyExercise);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-exercises"],
    queryFn: () => adminApi.exercises({}),
  });

  function closeModal() {
    setOpen(false);
    setForm(emptyExercise);
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
      payload.append("name", form.name.trim());
      payload.append("primary_muscle", form.muscle);
      payload.append("equipment", form.equipment);
      payload.append("exercise_type", form.kind);
      payload.append("secondary_muscles", JSON.stringify(form.secondary));
      form.photos.forEach((file) => payload.append("photos", file));
      if (form.video) payload.append("video", form.video);
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
    <div>
      <div className="page-head">
        <h1>Упражнения</h1>
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
      <Notice error={open ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить упражнения") : "")} success={success} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      <DataTable
        rows={data ?? []}
        columns={[
          { key: "id", label: "ID" },
          {
            key: "name",
            label: "Упражнение",
            render: (row) => (
              <EntityCell
                avatar={initials(row.name)}
                title={dash(row.name)}
                subtitle={muscleLabel(row.primary_muscle)}
              />
            ),
          },
          {
            key: "equipment",
            label: "Оборудование",
            render: (row) => <Badge tone="blue">{equipmentLabel(row.equipment)}</Badge>,
          },
          {
            key: "is_public",
            label: "Доступ",
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
      <Modal open={open} title="Новое упражнение" onClose={closeModal}>
        <Notice error={error} />
        <form className="stack-form" onSubmit={(e) => void onCreate(e)}>
          <label>
            Название
            <input
              value={form.name}
              onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
              required
            />
          </label>
          <div className="form-grid">
            <label>
              Основная мышца
              <Select
                value={form.muscle}
                onChange={(muscle) => setForm((current) => ({ ...current, muscle }))}
                options={muscles}
                placeholder="Мышца"
              />
            </label>
            <label>
              Тип
              <Select
                value={form.kind}
                onChange={(kind) => setForm((current) => ({ ...current, kind }))}
                options={kinds}
                placeholder="Тип"
              />
            </label>
            <label>
              Оборудование
              <Select
                value={form.equipment}
                onChange={(equipment) => setForm((current) => ({ ...current, equipment }))}
                options={equipmentOptions}
                placeholder="Оборудование"
                allowEmpty
                emptyLabel="Не указано"
              />
            </label>
          </div>
          <label>
            Дополнительные мышцы
            <ChipGroup
              options={muscles}
              values={form.secondary}
              onChange={(secondary) => setForm((current) => ({ ...current, secondary }))}
            />
          </label>
          <ImageField
            id="exercise-create-photos"
            files={form.photos}
            onFiles={(photos) => setForm((current) => ({ ...current, photos }))}
          />
          <FileField
            id="exercise-create-video"
            file={form.video}
            onFile={(video) => setForm((current) => ({ ...current, video }))}
          />
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
