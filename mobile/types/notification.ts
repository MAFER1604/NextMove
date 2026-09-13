export type NotificationScope = "global" | "session" | "recommendation" | "delivery";
export type NotificationType = "info" | "success" | "warning" | "error";

export interface AppNotification {
  id: string;
  type: NotificationType;
  message: string;
  scope: NotificationScope;
  dismissible: boolean;
  autoDismissMs?: number;
}
