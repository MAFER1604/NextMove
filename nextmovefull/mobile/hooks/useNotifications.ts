import { useCallback, useEffect, useRef, useState } from "react";
import { AppNotification, NotificationScope } from "../types/notification";

let counter = 0;
const nextId = () => `notif-${Date.now()}-${(++counter).toString(36)}`;

/**
 * Controlador central de notificaciones (sección 15 del brief).
 *
 * Reglas que cumple:
 *  - No se guardan dentro del estado persistente de la sesión (vive en su
 *    propio hook, no en useSession's state que se serializa/restaura).
 *  - Un temporizador por notificación, limpiado al descartarla (manual o auto).
 *  - No se duplica el mismo mensaje+scope mientras ya esté visible.
 *  - clearByScope() permite borrar solo lo que corresponde (p. ej. al llegar
 *    a SessionSummary se limpian "recommendation", "delivery" y "session").
 */
export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const clearTimer = (id: string) => {
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      delete timers.current[id];
    }
  };

  const dismiss = useCallback((id: string) => {
    clearTimer(id);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const notify = useCallback(
    (input: Omit<AppNotification, "id">) => {
      let createdId: string | null = null;
      setNotifications((prev) => {
        const duplicate = prev.find((n) => n.message === input.message && n.scope === input.scope);
        if (duplicate) return prev;
        const id = nextId();
        createdId = id;
        return [...prev, { ...input, id }];
      });
      // El id solo se conoce tras el setState; programamos el auto-dismiss
      // en un microtask para poder referenciarlo con seguridad.
      if (input.autoDismissMs) {
        setTimeout(() => {
          if (createdId) {
            timers.current[createdId] = setTimeout(() => dismiss(createdId!), input.autoDismissMs);
          }
        }, 0);
      }
      return createdId;
    },
    [dismiss]
  );

  const clearByScope = useCallback((...scopes: NotificationScope[]) => {
    setNotifications((prev) => {
      const toRemove = prev.filter((n) => scopes.includes(n.scope));
      toRemove.forEach((n) => clearTimer(n.id));
      return prev.filter((n) => !scopes.includes(n.scope));
    });
  }, []);

  const clearAll = useCallback(() => {
    Object.keys(timers.current).forEach(clearTimer);
    setNotifications([]);
  }, []);

  // Limpieza al desmontar (cambio de pantalla raíz, cierre de la app en dev, etc.)
  useEffect(() => {
    return () => {
      Object.keys(timers.current).forEach(clearTimer);
    };
  }, []);

  return { notifications, notify, dismiss, clearByScope, clearAll };
}
