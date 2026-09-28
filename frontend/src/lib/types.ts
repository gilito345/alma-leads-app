export type LeadState = "PENDING" | "REACHED_OUT";

export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
}

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  state: LeadState;
  resume: {
    filename: string;
    content_type: string;
    size_bytes: number;
  };
  reached_out_at: string | null;
  reached_out_by: UserSummary | null;
  created_at: string;
  updated_at: string;
}

export interface LeadPage {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: { field: string; message: string }[] | null;
  };
}

/** How the dashboard can show a resume in the page. See the API's `/resume/preview`. */
export interface ResumePreview {
  format: "pdf" | "html" | "unavailable";
  html: string | null;
}
