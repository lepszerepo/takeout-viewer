export interface MailListItem {
  id: number;
  event_id: number;
  dataset_id: number;
  dataset_name: string | null;
  folder: string | null;
  subject: string | null;
  from: { name?: string; email: string }[] | null;
  to: { name?: string; email: string }[] | null;
  cc: { name?: string; email: string }[] | null;
  labels: string[] | null;
  timestamp: string | null;
  size_bytes: number;
  has_attachments: boolean;
  thread_id: string | null;
  snippet: string | null;
}

export interface MailDetail extends MailListItem {
  bcc: { name?: string; email: string }[] | null;
  reply_to: { name?: string; email: string }[] | null;
  headers: Record<string, string> | null;
  attachments: { name: string; content_type?: string; size?: number }[] | null;
  message_id: string | null;
  in_reply_to: string | null;
  references: string[] | null;
  body_text: string | null;
  body_html: string | null;
  datasets: string[];
}

export interface FolderCount {
  folder: string;
  count: number;
}

export interface FtsResultItem {
  event_id: number;
  title: string;
  description: string | null;
  source: string;
  type: string;
  dataset_name: string;
  timestamp: string | null;
  folder: string | null;
  rank: number;
  snippet: string;
}

export interface TopCorrespondent {
  email: string;
  count: number;
}
