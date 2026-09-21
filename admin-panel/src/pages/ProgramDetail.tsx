import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { ChipGroup } from "../components/ChipGroup";
import { DetailLayout } from "../components/DetailLayout";
import { IconBtn, IconPencil, IconPlus, IconTrash } from "../components/IconBtn";
import { Modal } from "../components/Modal";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { dash, initials, labelOf } from "../lib/format";
import { toInt } from "../lib/numbers";
import { PROGRAM_STATUS_LABELS, PROGRAM_STATUS_OPTIONS, SOURCE_LABELS, useDictLabel, useDictOptions } from "../lib/options";

const emptyDay = {
  title: "",
  description: "",
  duration: "",
  muscles: [] as string[],
};

const emptyEx = {
  exerciseId: "",
  sets: "3",
  repsMin: "8",
  repsMax: "12",
  note: "",
};

function exerciseStats(item: Record<string, unknown>) {
  const sets = item.sets == null || item.sets === "" ? "" : `${item.sets} ×`;
  const min = item.reps_min == null ? "" : String(item.reps_min);
  const max = item.reps_max == null ? "" : String(item.reps_max);
  const reps = min && max ? `${min}–${max}` : min || max;
  return { sets, reps };
}

export function ProgramDetailPage() {
  const { id } = useParams();
  const programId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const levels = useDictOptions("workout_level");
  const goalOptions = useDictOptions("fitness_goal");
  const equipmentOptions = useDictOptions("equipment");
  const muscleOptions = useDictOptions("muscle_group");
  const muscleLabel = useDictLabel("muscle_group");
  const levelLabel = useDictLabel("workout_level");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [level, setLevel] = useState("beginner");
  const [status, setStatus] = useState("published");
  const [goals, setGoals] = useState<string[]>([]);
  const [equipment, setEquipment] = useState<string[]>([]);
  const [workoutsPerWeek, setWorkoutsPerWeek] = useState("");
  const [durationWeeks, setDurationWeeks] = useState("");
  const [isPro, setIsPro] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dayOpen, setDayOpen] = useState(false);
  const [editingDayId, setEditingDayId] = useState<number | null>(null);
  const [dayForm, setDayForm] = useState(emptyDay);
  const [daySaving, setDaySaving] = useState(false);
  const [exOpen, setExOpen] = useState(false);
  const [exDayId, setExDayId] = useState<number | null>(null);
  const [editingExId, setEditingExId] = useState<number | null>(null);
  const [exForm, setExForm] = useState(emptyEx);
  const [exSaving, setExSaving] = useState(false);
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-program", programId],
    queryFn: () => adminApi.program(programId),
    enabled: Number.isFinite(programId),
  });
  const { data: exerciseRows } = useQuery({
    queryKey: ["admin-exercises"],
    queryFn: () => adminApi.exercises({}),
  });
  const days = Array.isArray(data?.days) ? (data.days as Record<string, unknown>[]) : [];
  const exerciseOptions = (exerciseRows ?? []).map((row) => ({
    value: String(row.id),
    label: String(row.name ?? `ID ${row.id}`),
  }));

  useEffect(() => {
    if (!data) return;
    setTitle(String(data.title ?? ""));
    setDescription(String(data.description ?? ""));
    setLevel(String(data.level ?? "beginner"));
    setStatus(String(data.status ?? "published"));
    setGoals(Array.isArray(data.goals) ? data.goals.map(String) : []);
    setEquipment(Array.isArray(data.equipment) ? data.equipment.map(String) : []);
    setWorkoutsPerWeek(data.workouts_per_week == null ? "" : String(data.workouts_per_week));
    setDurationWeeks(data.duration_weeks == null ? "" : String(data.duration_weeks));
    setIsPro(Boolean(data.is_pro));
  }, [data]);

  async function refreshProgram() {
    await queryClient.invalidateQueries({ queryKey: ["admin-program", programId] });
  }

  function closeDayModal() {
    setDayOpen(false);
    setEditingDayId(null);
    setDayForm(emptyDay);
    setDaySaving(false);
  }

  function openDayCreate() {
    setError("");
    setEditingDayId(null);
    setDayForm(emptyDay);
    setDayOpen(true);
  }

  function openDayEdit(day: Record<string, unknown>) {
    setError("");
    setEditingDayId(Number(day.id));
    setDayForm({
      title: String(day.title ?? ""),
      description: String(day.description ?? ""),
      duration: day.duration_min == null ? "" : String(day.duration_min),
      muscles: Array.isArray(day.focus_muscles) ? day.focus_muscles.map(String) : [],
    });
    setDayOpen(true);
  }

  function closeExModal() {
    setExOpen(false);
    setExDayId(null);
    setEditingExId(null);
    setExForm(emptyEx);
    setExSaving(false);
  }

  function openExCreate(dayId: number) {
    setError("");
    setExDayId(dayId);
    setEditingExId(null);
    setExForm({ ...emptyEx, exerciseId: exerciseOptions[0]?.value ?? "" });
    setExOpen(true);
  }

  function openExEdit(dayId: number, item: Record<string, unknown>) {
    setError("");
    setExDayId(dayId);
    setEditingExId(Number(item.id));
    setExForm({
      exerciseId: String(item.exercise_id ?? ""),
      sets: item.sets == null ? "" : String(item.sets),
      repsMin: item.reps_min == null ? "" : String(item.reps_min),
      repsMax: item.reps_max == null ? "" : String(item.reps_max),
      note: String(item.note ?? ""),
    });
    setExOpen(true);
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!data) return;
    setError("");
    setSuccess("");
    try {
      await adminApi.updateProgram(programId, {
        title,
        description,
        level,
        status,
        goals,
        equipment,
        workouts_per_week: toInt(workoutsPerWeek),
        duration_weeks: toInt(durationWeeks),
        is_pro: isPro,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin-programs"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-program", programId] });
      navigate("/programs", { state: { success: "Программа сохранена" } });
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить программу"));
    }
  }

  async function onSaveDay(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setDaySaving(true);
    const payload = {
      title: dayForm.title.trim(),
      description: dayForm.description.trim() || null,
      duration_min: toInt(dayForm.duration),
      focus_muscles: dayForm.muscles,
    };
    try {
      if (editingDayId) {
        await adminApi.updateProgramDay(programId, editingDayId, payload);
        setSuccess("День обновлён");
      } else {
        await adminApi.createProgramDay(programId, payload);
        setSuccess("День добавлен");
      }
      closeDayModal();
      await refreshProgram();
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить день"));
      setDaySaving(false);
    }
  }

  async function onDeleteDay(dayId: number) {
    setError("");
    setSuccess("");
    try {
      await adminApi.deleteProgramDay(programId, dayId);
      setSuccess("День удалён");
      await refreshProgram();
    } catch (err) {
      setError(apiError(err, "Не удалось удалить день"));
    }
  }

  async function onSaveExercise(event: FormEvent) {
    event.preventDefault();
    if (!exDayId) return;
    if (!exForm.exerciseId) {
      setError("Выберите упражнение");
      return;
    }
    setError("");
    setSuccess("");
    setExSaving(true);
    const payload = {
      exercise_id: Number(exForm.exerciseId),
      sets: toInt(exForm.sets),
      reps_min: toInt(exForm.repsMin),
      reps_max: toInt(exForm.repsMax),
      note: exForm.note.trim() || null,
    };
    try {
      if (editingExId) {
        await adminApi.updateProgramDayExercise(programId, exDayId, editingExId, payload);
        setSuccess("Упражнение обновлено");
      } else {
        await adminApi.addProgramDayExercise(programId, exDayId, payload);
        setSuccess("Упражнение добавлено");
      }
      closeExModal();
      await refreshProgram();
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить упражнение"));
      setExSaving(false);
    }
  }

  async function onDeleteExercise(dayId: number, itemId: number) {
    setError("");
    setSuccess("");
    try {
      await adminApi.deleteProgramDayExercise(programId, dayId, itemId);
      setSuccess("Упражнение убрано");
      await refreshProgram();
    } catch (err) {
      setError(apiError(err, "Не удалось убрать упражнение"));
    }
  }

  return (
    <DetailLayout
      backTo="/programs"
      title={data ? String(data.title) : "Программа"}
      subtitle={data ? levelLabel(data.level) : undefined}
      avatar={data ? initials(data.title) : "П"}
      meta={data ? `ID ${data.id} · сохранений ${dash(data.saves_count)}` : undefined}
      badges={
        data ? (
          <>
            <Badge tone={status === "published" ? "lime" : status === "archived" ? "muted" : "orange"}>
              {labelOf(PROGRAM_STATUS_LABELS, data.status)}
            </Badge>
            <Badge>{labelOf(SOURCE_LABELS, data.source)}</Badge>
            {data.is_pro ? <Badge tone="lime">PRO</Badge> : null}
          </>
        ) : null
      }
    >
      <Notice
        error={dayOpen || exOpen ? "" : error || (loadError ? apiError(loadError, "Не удалось загрузить программу") : "")}
        success={dayOpen || exOpen ? "" : success}
      />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <Section title="Параметры">
          <form className="stack-form" onSubmit={(e) => void onSave(e)}>
            <label>
              Название
              <input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </label>
            <label>
              Описание
              <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>
            <div className="form-grid">
              <label>
                Уровень
                <Select value={level} onChange={setLevel} options={levels} placeholder="Уровень" />
              </label>
              <label>
                Статус
                <Select value={status} onChange={setStatus} options={PROGRAM_STATUS_OPTIONS} />
              </label>
              <label>
                Тренировок в неделю
                <input type="number" min={1} max={14} value={workoutsPerWeek} onChange={(e) => setWorkoutsPerWeek(e.target.value)} />
              </label>
              <label>
                Длительность, недель
                <input type="number" min={1} max={52} value={durationWeeks} onChange={(e) => setDurationWeeks(e.target.value)} />
              </label>
            </div>
            <label>
              Цели
              <ChipGroup options={goalOptions} values={goals} onChange={setGoals} />
            </label>
            <label>
              Оборудование
              <ChipGroup options={equipmentOptions} values={equipment} onChange={setEquipment} />
            </label>
            <label className="check-row">
              <input type="checkbox" checked={isPro} onChange={(e) => setIsPro(e.target.checked)} />
              PRO-программа
            </label>
            <div className="modal-actions">
              <button type="submit">Сохранить</button>
            </div>
          </form>
        </Section>
      ) : null}
      <Section
        title="Дни программы"
        actions={
          data ? (
            <button type="button" onClick={openDayCreate}>
              Добавить день
            </button>
          ) : null
        }
      >
        {days.length ? (
          <div className="day-stack">
            {days.map((day, index) => {
              const exercises = Array.isArray(day.exercises) ? (day.exercises as Record<string, unknown>[]) : [];
              const muscles = Array.isArray(day.focus_muscles) ? day.focus_muscles.map(String) : [];
              return (
                <article key={String(day.id)} className="day-card">
                  <div className="day-card-head">
                    <div className="day-index">{String(index + 1).padStart(2, "0")}</div>
                    <div className="day-card-copy">
                      <div className="day-title-row">
                        <h3>{dash(day.title)}</h3>
                        {day.duration_min ? <span className="day-pill">{dash(day.duration_min)} мин</span> : null}
                        <span className="day-pill day-pill-muted">
                          {exercises.length
                            ? `${exercises.length} упр.`
                            : "без упражнений"}
                        </span>
                      </div>
                      {day.description ? <p className="day-desc">{dash(day.description)}</p> : null}
                      {muscles.length ? (
                        <div className="badge-row">
                          {muscles.map((code) => (
                            <Badge key={code} tone="blue">
                              {muscleLabel(code)}
                            </Badge>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <div className="row-actions">
                      <IconBtn title="Добавить упражнение" onClick={() => openExCreate(Number(day.id))}>
                        <IconPlus />
                      </IconBtn>
                      <IconBtn tone="muted" title="Изменить день" onClick={() => openDayEdit(day)}>
                        <IconPencil />
                      </IconBtn>
                      <IconBtn tone="red" title="Удалить день" onClick={() => void onDeleteDay(Number(day.id))}>
                        <IconTrash />
                      </IconBtn>
                    </div>
                  </div>
                  {exercises.length ? (
                    <ul className="day-ex-list">
                      {exercises.map((item, exIndex) => {
                        const stats = exerciseStats(item);
                        return (
                          <li key={String(item.id)} className="day-ex">
                            <span className="day-ex-num">{exIndex + 1}</span>
                            <div className="day-ex-copy">
                              <strong>{dash(item.name)}</strong>
                              {item.note ? <p>{dash(item.note)}</p> : null}
                            </div>
                            <div className="day-ex-stats">
                              {stats.sets ? <span>{stats.sets}</span> : null}
                              {stats.reps ? <span>{stats.reps}</span> : null}
                            </div>
                            <div className="row-actions">
                              <IconBtn tone="muted" title="Изменить" onClick={() => openExEdit(Number(day.id), item)}>
                                <IconPencil />
                              </IconBtn>
                              <IconBtn
                                tone="red"
                                title="Убрать"
                                onClick={() => void onDeleteExercise(Number(day.id), Number(item.id))}
                              >
                                <IconTrash />
                              </IconBtn>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <button type="button" className="day-ex-empty" onClick={() => openExCreate(Number(day.id))}>
                      <IconPlus />
                      Добавить упражнение из каталога
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        ) : (
          <div className="empty-days">
            <p>Пока нет тренировочных дней</p>
            <span>Добавьте день, затем соберите упражнения из каталога.</span>
            <button type="button" onClick={openDayCreate}>
              Добавить день
            </button>
          </div>
        )}
      </Section>
      <Modal open={dayOpen} title={editingDayId ? "Изменить день" : "Новый день"} onClose={closeDayModal}>
        <Notice error={error} />
        <form className="stack-form" onSubmit={(e) => void onSaveDay(e)}>
          <label>
            Название
            <input
              value={dayForm.title}
              onChange={(e) => setDayForm((current) => ({ ...current, title: e.target.value }))}
              placeholder="Жимы"
              required
            />
          </label>
          <label>
            Описание
            <textarea
              rows={3}
              value={dayForm.description}
              onChange={(e) => setDayForm((current) => ({ ...current, description: e.target.value }))}
            />
          </label>
          <label>
            Длительность, мин
            <input
              type="number"
              min={1}
              max={300}
              value={dayForm.duration}
              onChange={(e) => setDayForm((current) => ({ ...current, duration: e.target.value }))}
            />
          </label>
          <label>
            Фокус мышц
            <ChipGroup options={muscleOptions} values={dayForm.muscles} onChange={(muscles) => setDayForm((current) => ({ ...current, muscles }))} />
          </label>
          <div className="modal-actions">
            <button type="button" className="ghost" onClick={closeDayModal}>
              Отмена
            </button>
            <button type="submit" disabled={daySaving}>
              {daySaving ? "Сохранение..." : "Сохранить"}
            </button>
          </div>
        </form>
      </Modal>
      <Modal open={exOpen} title={editingExId ? "Изменить упражнение" : "Упражнение дня"} onClose={closeExModal}>
        <Notice error={error} />
        {exerciseOptions.length ? (
          <form className="stack-form" onSubmit={(e) => void onSaveExercise(e)}>
            <label>
              Упражнение
              <Select
                value={exForm.exerciseId}
                onChange={(exerciseId) => setExForm((current) => ({ ...current, exerciseId }))}
                options={exerciseOptions}
                placeholder="Выберите упражнение"
              />
            </label>
            <div className="form-grid">
              <label>
                Подходы
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={exForm.sets}
                  onChange={(e) => setExForm((current) => ({ ...current, sets: e.target.value }))}
                />
              </label>
              <label>
                Повт. от
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={exForm.repsMin}
                  onChange={(e) => setExForm((current) => ({ ...current, repsMin: e.target.value }))}
                />
              </label>
              <label>
                Повт. до
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={exForm.repsMax}
                  onChange={(e) => setExForm((current) => ({ ...current, repsMax: e.target.value }))}
                />
              </label>
            </div>
            <label>
              Заметка
              <input
                value={exForm.note}
                onChange={(e) => setExForm((current) => ({ ...current, note: e.target.value }))}
              />
            </label>
            <div className="modal-actions">
              <button type="button" className="ghost" onClick={closeExModal}>
                Отмена
              </button>
              <button type="submit" disabled={exSaving}>
                {exSaving ? "Сохранение..." : "Сохранить"}
              </button>
            </div>
          </form>
        ) : (
          <p className="muted">Сначала добавьте упражнения в каталог.</p>
        )}
      </Modal>
    </DetailLayout>
  );
}
