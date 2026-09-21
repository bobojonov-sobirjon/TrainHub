import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/resources";
import { ChipGroup } from "../components/ChipGroup";
import { DetailLayout } from "../components/DetailLayout";
import { Notice } from "../components/Notice";
import { Select } from "../components/Select";
import { Badge, Section } from "../components/Ui";
import { apiError } from "../lib/apiError";
import { initials } from "../lib/format";
import { useDictLabel, useDictOptions } from "../lib/options";

export function ExerciseDetailPage() {
  const { id } = useParams();
  const exerciseId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const muscles = useDictOptions("muscle_group");
  const equipmentOptions = useDictOptions("equipment");
  const kinds = useDictOptions("workout_kind");
  const muscleLabel = useDictLabel("muscle_group");
  const kindLabel = useDictLabel("workout_kind");
  const [name, setName] = useState("");
  const [muscle, setMuscle] = useState("");
  const [equipment, setEquipment] = useState("");
  const [kind, setKind] = useState("strength");
  const [secondary, setSecondary] = useState<string[]>([]);
  const [photoUrl, setPhotoUrl] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [error, setError] = useState("");
  const { data, isLoading, error: loadError } = useQuery({
    queryKey: ["admin-exercise", exerciseId],
    queryFn: () => adminApi.exercise(exerciseId),
    enabled: Number.isFinite(exerciseId),
  });

  useEffect(() => {
    if (!data) return;
    setName(String(data.name ?? ""));
    setMuscle(String(data.primary_muscle ?? ""));
    setEquipment(String(data.equipment ?? ""));
    setKind(String(data.exercise_type ?? "strength"));
    setSecondary(Array.isArray(data.secondary_muscles) ? data.secondary_muscles.map(String) : []);
    setPhotoUrl(String(data.photo_url ?? ""));
    setVideoUrl(String(data.video_url ?? ""));
  }, [data]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!data) return;
    setError("");
    try {
      await adminApi.updateExercise(exerciseId, {
        name,
        primary_muscle: muscle,
        equipment: equipment || null,
        secondary_muscles: secondary,
        exercise_type: kind,
        photo_url: photoUrl.trim() || null,
        video_url: videoUrl.trim() || null,
      });
      await queryClient.invalidateQueries({ queryKey: ["admin-exercises"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-exercise", exerciseId] });
      navigate("/exercises", { state: { success: "Упражнение сохранено" } });
    } catch (err) {
      setError(apiError(err, "Не удалось сохранить упражнение"));
    }
  }

  return (
    <DetailLayout
      backTo="/exercises"
      title={data ? String(data.name) : "Упражнение"}
      subtitle={data ? muscleLabel(data.primary_muscle) : undefined}
      avatar={data ? initials(data.name) : "У"}
      meta={data ? `ID ${data.id}` : undefined}
      badges={
        data ? (
          <>
            <Badge tone="blue">{kindLabel(data.exercise_type)}</Badge>
            {data.is_public ? <Badge tone="lime">публичное</Badge> : <Badge>личное</Badge>}
          </>
        ) : null
      }
    >
      <Notice error={error || (loadError ? apiError(loadError, "Не удалось загрузить упражнение") : "")} />
      {isLoading ? <p className="muted">Загрузка...</p> : null}
      {data ? (
        <Section title="Параметры">
          <form className="stack-form" onSubmit={(e) => void onSave(e)}>
            <label>
              Название
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <div className="form-grid">
              <label>
                Основная мышца
                <Select value={muscle} onChange={setMuscle} options={muscles} placeholder="Мышца" />
              </label>
              <label>
                Тип
                <Select value={kind} onChange={setKind} options={kinds} placeholder="Тип" />
              </label>
              <label>
                Оборудование
                <Select
                  value={equipment}
                  onChange={setEquipment}
                  options={equipmentOptions}
                  placeholder="Оборудование"
                  allowEmpty
                  emptyLabel="Не указано"
                />
              </label>
            </div>
            <label>
              Дополнительные мышцы
              <ChipGroup options={muscles} values={secondary} onChange={setSecondary} />
            </label>
            {photoUrl ? <img className="preview-img" src={photoUrl} alt="" /> : null}
            <label>
              Фото (URL)
              <input value={photoUrl} onChange={(e) => setPhotoUrl(e.target.value)} placeholder="https://" />
            </label>
            <label>
              Видео (URL)
              <input value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} placeholder="https://" />
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
