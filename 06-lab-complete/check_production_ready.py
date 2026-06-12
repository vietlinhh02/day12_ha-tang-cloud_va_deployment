"""
Production Readiness Checker — Discord Class Bot
Kiểm tra project đủ điều kiện deploy chưa.
Chạy: python check_production_ready.py
"""
import os
import sys


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "" if passed else ""
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    return {"name": name, "passed": passed}


def check_file(base: str, path: str) -> bool:
    return os.path.exists(os.path.join(base, path))


def run_checks():
    results = []
    base = os.path.dirname(__file__)

    print("\n" + "=" * 55)
    print("  Production Readiness Check — Discord Class Bot")
    print("=" * 55)

    #  Required Files 
    print("\n Required Files")
    for f in ["Dockerfile", "docker-compose.yml", ".dockerignore",
              ".env.example", "requirements.txt", "pyproject.toml",
              "railway.toml", "render.yaml"]:
        results.append(check(f"{f} exists", check_file(base, f)))

    #  Bot Structure 
    print("\n Bot Structure")
    bot_files = [
        "bot/__init__.py", "bot/main.py", "bot/config.py",
        "bot/llm.py", "bot/agent.py", "bot/cog_qa.py",
        "bot/rag.py", "bot/corrections.py",
    ]
    for f in bot_files:
        exists = check_file(base, f)
        results.append(check(f"  {f}", exists, "" if exists else "Missing!"))

    #  Security 
    print("\n Security")
    gitignore = os.path.join(base, "..", ".gitignore")
    env_ignored = False
    if os.path.exists(gitignore):
        content = open(gitignore).read()
        if ".env" in content:
            env_ignored = True
    results.append(check(".env in .gitignore", env_ignored,
                         "Add .env to .gitignore!" if not env_ignored else ""))

    # Check no hardcoded secrets
    secrets_found = []
    for root, dirs, files in os.walk(os.path.join(base, "bot")):
        for f in files:
            if f.endswith(".py"):
                content = open(os.path.join(root, f)).read()
                for bad in ["sk-", "password123", "hardcoded"]:
                    if bad in content:
                        secrets_found.append(f"{f}:{bad}")
    results.append(check("No hardcoded secrets in code",
                         len(secrets_found) == 0,
                         str(secrets_found) if secrets_found else ""))

    #  Docker 
    print("\n Docker")
    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        content = open(dockerfile).read()
        results.append(check("Multi-stage build",
                             "AS builder" in content and "AS runtime" in content))
        results.append(check("Non-root user",
                             "useradd" in content or "USER " in content))
        results.append(check("Slim base image",
                             "slim" in content or "alpine" in content))

    dockerignore = os.path.join(base, ".dockerignore")
    if os.path.exists(dockerignore):
        content = open(dockerignore).read()
        results.append(check(".dockerignore covers .env", ".env" in content))
        results.append(check(".dockerignore covers __pycache__",
                             "__pycache__" in content))

    #  Config Validation 
    print("\n Config")
    config_py = os.path.join(base, "bot", "config.py")
    if os.path.exists(config_py):
        content = open(config_py).read()
        checks = [
            ("DISCORD_TOKEN", "discord_token"),
            ("DEEPSEEK_API_KEY", "deepseek_api_key"),
        ]
        for name, var in checks:
            results.append(check(f"  {name} configured", var in content))

    #  Summary 
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = round(passed / total * 100)

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")

    if pct == 100:
        print("   PRODUCTION READY! Deploy nào!")
    elif pct >= 80:
        print("   Almost there! Fix the  items above.")
    elif pct >= 60:
        print("    Good progress. Several items need attention.")
    else:
        print("   Not ready. Review the checklist carefully.")

    print("=" * 55 + "\n")
    return pct == 100


if __name__ == "__main__":
    ready = run_checks()
    sys.exit(0 if ready else 1)
