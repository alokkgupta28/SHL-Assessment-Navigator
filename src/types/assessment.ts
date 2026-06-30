export type JobLevel = "Entry" | "Mid" | "Senior" | "Manager" | "Executive";

export interface Assessment {
  id: string;
  name: string;
  category: string;
  durationMinutes: number;
  jobLevels: JobLevel[];
  adaptive: boolean;
  remote: boolean;
  languages: string[];
  skills: string[];
  description: string;
  officialUrl: string;
}
