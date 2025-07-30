import os
import subprocess

# 1. 이동할 Git 저장소 경로
repo_path = r"C:\Users\EDU03-16\Documents\GitHub\0730-team-project"  # 본인 경로로 변경하세요

# 2. 제거할 파일 이름
file_to_remove = "0730-team-project.zip"

# 3. 저장소 경로로 이동
os.chdir(repo_path)

# 4. git-filter-repo 명령어 실행 (파일 제거)
subprocess.run([
    "git", "filter-repo",
    f"--path", file_to_remove,
    "--invert-paths"
], shell=True)

# 5. 강제 푸시 (주의: 원격 저장소 기록 덮어씀)
subprocess.run(["git", "push", "--force"], shell=True)

print("✅ 완료: 대용량 파일 제거 및 강제 푸시 완료")
