export type Role = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  streaming?: boolean;
}

export type ChatStatus = "idle" | "thinking" | "streaming" | "error";
