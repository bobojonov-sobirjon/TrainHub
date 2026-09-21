import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export function useFlashSuccess() {
  const location = useLocation();
  const navigate = useNavigate();
  const [success, setSuccess] = useState("");
  const flash =
    location.state && typeof location.state === "object" && "success" in location.state
      ? String((location.state as { success?: unknown }).success ?? "")
      : "";

  useEffect(() => {
    if (!flash) return;
    setSuccess(flash);
    navigate(location.pathname, { replace: true, state: {} });
  }, [flash, location.pathname, navigate]);

  return { success, setSuccess };
}
