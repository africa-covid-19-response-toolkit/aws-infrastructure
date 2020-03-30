service_name = "response-app-api"
github_url   = "https://github.com/amexboy/CovidCallReporterApi"
branch       = "dev"
port         = 80
health_url   = "/"
secrets = [
  { name = "DB_PASSWORD", valueFrom = "/response-app/db/password" }
]

envs = [
  { name = "DB_HOST", value = "response_app.db.local" },
  { name = "DB_PORT", value = "3306" },
  { name = "DB_DATABASE", value = "response_app" },
  { name = "DB_USERNAME", value = "admin" },
]
