$BackupDir = ".\backups"

if (!(Test-Path -Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$DateStr = Get-Date -Format "yyyy-MM-dd_HH-mm"
$FileName = "db_backup_$DateStr.sql"
$FilePath = Join-Path -Path $BackupDir -ChildPath $FileName

docker-compose exec -T -e PGPASSWORD="1234" db pg_dump -U postgres car_service_db > $FilePath

# Находим и удаляем файлы старше 7 дней
Get-ChildItem -Path $BackupDir -Filter "*.sql" | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-7) } | Remove-Item -ErrorAction SilentlyContinue
