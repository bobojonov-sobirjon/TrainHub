import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { ChipGroup } from "../components/ChipGroup";
import { DataTable } from "../components/DataTable";
import { IconArchive, IconBtn, IconOpen } from "../components/IconBtn";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { ImageField } from "../components/MediaFields";
import { Badge, EntityCell } from "../components/Ui";
import { useFlashSuccess } from "../hooks/useFlashSuccess";
import { apiError } from "../lib/apiError";
import { toInt } from "../lib/numbers";
import { PROGRAM_STATUS_LABELS, PROGRAM_STATUS_OPTIONS, SOURCE_LABELS, useDictLabel, useDictOptions } from "../lib/options";
import { dash, initials, labelOf } from "../lib/format";

const emptyProgram = {
  title: "",
  description: "",
  level: "beginner",
  status: "published",
  goals: [] as string[],
  equipment: [] as string[],
  workoutsPerWeek: "",
  durationWeeks: "",
  isPro: false,
  cover: [] as File[],
};

export function ProgramsPage() {
  const queryClient = useQueryClient();
  const levels = useDictOptions("workout_level");
  const goals = useDictOptions("fitness_goal");
  const equipment = useDictOptions("equipment");
  const levelLabel = useDictLabel("workout_level");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyProgram);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { success, setSuccess } = useFlashSuccess();
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-programs"],
    queryFn: () => adminApi.programs({ page: 1, page_size: 50 }),
  });

  function closeModal() {
    setOpen(false);
    setForm(emptyProgram);
    setSaving(false);
    setError("");
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const created = await adminApi.createProgram({
        title: form.title.trim(),
        description: form.description.trim() || null,
        level: form.level,
        status: form.status,
        goals: form.goals,
        equipment: form.equipment,
        workouts_per_week: toInt(form.workoutsPerWeek),
        duration_weeks: toInt(form.durationWeeks),
        is_pro: form.isPro,
        source: "catalog",
      });
      const id = Number(created.data?.data?.id);
      if (id && form.cover[0]) {
        await adminApi.uploadProgramCover(id, form.cover[0]);
      }
      closeModal();
      await queryClient.invalidateQueries({ queryKey: ["admin-programs"] });
      setSuccess("Программа создана");
    } catch (err) {
      setError(apiError(err, "Не удалось создать программу"));
      setSaving(false);
    }
  }

  async function onArchive(id: number) {
    setError("");
    setSuccess("");
    try {
      await adminApi.archiveProgram(id);
      await queryClient.invalidateQueries({ queryKey: ["admin-programs"] });
      setSuccess("Программа архивирована");
    } catch (err) {
      setError(apiError(err, "Не удалось архивировать программу"));
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1>Программы</h1>
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
      <Notice error={open ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить программы") : "")} success={success} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      <DataTable
        rows={data?.items ?? []}
        columns={[
          { key: "id", label: "ID" },
          {
            key: "title",
            label: "Программа",
            render: (row) => (
              <EntityCell
                avatar={initials(row.title)}
                title={dash(row.title)}
                subtitle={levelLabel(row.level)}
              />
            ),
          },
          {
            key: "status",
            label: "Статус",
            render: (row) => (
              <Badge tone={row.status === "published" ? "lime" : row.status === "archived" ? "muted" : "orange"}>
                {labelOf(PROGRAM_STATUS_LABELS, row.status)}
              </Badge>
            ),
          },
          {
            key: "source",
            label: "Источник",
            render: (row) => <Badge>{labelOf(SOURCE_LABELS, row.source)}</Badge>,
          },
          {
            key: "is_pro",
            label: "PRO",
            render: (row) => (row.is_pro ? <Badge tone="lime">PRO</Badge> : <Badge>нет</Badge>),
          },
          { key: "saves_count", label: "Сохранения" },
          {
            key: "actions",
            label: "",
            render: (row) => (
              <div className="row-actions">
                <IconBtn to={`/programs/${row.id}`} title="Открыть">
                  <IconOpen />
                </IconBtn>
                <IconBtn tone="muted" title="В архив" onClick={() => void onArchive(Number(row.id))}>
                  <IconArchive />
                </IconBtn>
              </div>
            ),
          },
        ]}
      />
      <Modal open={open} title="Новая программа" onClose={closeModal}>
        <Notice error={error} />
        <form className="stack-form" onSubmit={(e) => void onCreate(e)}>
          <label>
            Название
            <input
              value={form.title}
              onChange={(e) => setForm((current) => ({ ...current, title: e.target.value }))}
              required
            />
          </label>
          <label>
            Описание
            <textarea
              rows={4}
              value={form.description}
              onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))}
            />
          </label>
          <div className="form-grid">
            <label>
              Уровень
              <Select
                value={form.level}
                onChange={(level) => setForm((current) => ({ ...current, level }))}
                options={levels}
                placeholder="Уровень"
              />
            </label>
            <label>
              Статус
              <Select
                value={form.status}
                onChange={(status) => setForm((current) => ({ ...current, status }))}
                options={PROGRAM_STATUS_OPTIONS}
              />
            </label>
            <label>
              Тренировок в неделю
              <input
                type="number"
                min={1}
                max={14}
                value={form.workoutsPerWeek}
                onChange={(e) => setForm((current) => ({ ...current, workoutsPerWeek: e.target.value }))}
              />
            </label>
            <label>
              Длительность, недель
              <input
                type="number"
                min={1}
                max={52}
                value={form.durationWeeks}
                onChange={(e) => setForm((current) => ({ ...current, durationWeeks: e.target.value }))}
              />
            </label>
          </div>
          <label>
            Цели
            <ChipGroup
              options={goals}
              values={form.goals}
              onChange={(next) => setForm((current) => ({ ...current, goals: next }))}
            />
          </label>
          <label>
            Оборудование
            <ChipGroup
              options={equipment}
              values={form.equipment}
              onChange={(next) => setForm((current) => ({ ...current, equipment: next }))}
            />
          </label>
          <label className="check-row">
            <input
              type="checkbox"
              checked={form.isPro}
              onChange={(e) => setForm((current) => ({ ...current, isPro: e.target.checked }))}
            />
            PRO-программа
          </label>
          <ImageField
            id="program-create-cover"
            label="Обложка"
            hint="Одно изображение обложки: JPG, PNG, WEBP или GIF."
            multiple={false}
            files={form.cover}
            onFiles={(cover) => setForm((current) => ({ ...current, cover }))}
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
