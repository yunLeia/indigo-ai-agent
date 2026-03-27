function requireServerEnv(name: string) {
  const value = process.env[name];

  if (!value) {
    throw new Error(`Missing server environment variable: ${name}`);
  }

  return value;
}

export const serverEnv = {
  databaseUrl: requireServerEnv("DATABASE_URL"),
  geminiApiKey: process.env.GEMINI_API_KEY ?? "",
  geminiModel: process.env.GEMINI_MODEL ?? "gemini-2.5-flash",
  googleCloudLocation: process.env.GOOGLE_CLOUD_LOCATION ?? "us-central1",
  googleCloudProjectId: process.env.GOOGLE_CLOUD_PROJECT_ID ?? "",
  supabaseServiceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY ?? "",
};
