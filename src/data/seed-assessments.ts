import type { Assessment } from "@/types/assessment";

// UI seed data only — used to render the recommendations rail with real visuals.
// Replace with a backend-driven recommendation call later. No hardcoded "AI output".
export const seedAssessments: Assessment[] = [
  {
    id: "java-dev-8-0",
    name: "Java Developer (New)",
    category: "Technology",
    durationMinutes: 40,
    jobLevels: ["Mid", "Senior"],
    adaptive: true,
    remote: true,
    languages: ["English", "French", "German", "Spanish"],
    skills: ["Java", "OOP", "Spring", "Concurrency", "JVM"],
    description:
      "Adaptive assessment measuring Java programming knowledge across syntax, object-oriented principles, concurrency, and the Spring ecosystem.",
    officialUrl: "https://www.shl.com/solutions/products/product-catalog/",
  },
  {
    id: "frontend-react",
    name: "Front-end Developer (React)",
    category: "Technology",
    durationMinutes: 35,
    jobLevels: ["Mid", "Senior"],
    adaptive: true,
    remote: true,
    languages: ["English"],
    skills: ["React", "TypeScript", "CSS", "Accessibility", "State management"],
    description:
      "Evaluates modern front-end engineering capability with React, TypeScript and component architecture, including accessibility fundamentals.",
    officialUrl: "https://www.shl.com/solutions/products/product-catalog/",
  },
  {
    id: "ocean-personality",
    name: "Occupational Personality Questionnaire (OPQ32)",
    category: "Personality",
    durationMinutes: 25,
    jobLevels: ["Mid", "Senior", "Manager", "Executive"],
    adaptive: false,
    remote: true,
    languages: ["English", "French", "German", "Spanish", "Portuguese", "Japanese"],
    skills: ["Behavioural style", "Leadership potential", "Team dynamics"],
    description:
      "The world's most widely used measure of workplace personality, profiling 32 behavioural traits relevant to job performance.",
    officialUrl: "https://www.shl.com/solutions/products/product-catalog/",
  },
  {
    id: "verify-numerical",
    name: "Verify G+ Numerical Reasoning",
    category: "Cognitive",
    durationMinutes: 18,
    jobLevels: ["Entry", "Mid"],
    adaptive: true,
    remote: true,
    languages: ["English", "German", "Spanish", "Mandarin"],
    skills: ["Numerical reasoning", "Data interpretation"],
    description:
      "Adaptive numerical reasoning test measuring the ability to interpret and reason with numerical data presented in tables and graphs.",
    officialUrl: "https://www.shl.com/solutions/products/product-catalog/",
  },
  {
    id: "leadership-assessment",
    name: "SHL Leadership Assessment",
    category: "Leadership",
    durationMinutes: 60,
    jobLevels: ["Manager", "Executive"],
    adaptive: false,
    remote: true,
    languages: ["English", "French", "German"],
    skills: ["Strategic thinking", "Influence", "People leadership", "Execution"],
    description:
      "Comprehensive leadership profile assessing strategic, operational and people leadership capabilities aligned to executive competency models.",
    officialUrl: "https://www.shl.com/solutions/products/product-catalog/",
  },
  {
    id: "sales-professional",
    name: "Sales Professional Solution",
    category: "Sales",
    durationMinutes: 30,
    jobLevels: ["Entry", "Mid", "Senior"],
    adaptive: false,
    remote: true,
    languages: ["English", "Spanish", "Portuguese"],
    skills: ["Prospecting", "Negotiation", "Customer focus", "Resilience"],
    description:
      "End-to-end profile of sales aptitude including behavioural fit, situational judgement and cognitive ability for B2B sales roles.",
    officialUrl: "https://www.shl.com/solutions/products/product-catalog/",
  },
];

export const findAssessment = (id: string) =>
  seedAssessments.find((a) => a.id === id);
