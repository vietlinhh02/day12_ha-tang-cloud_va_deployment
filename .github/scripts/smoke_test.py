"""
Smoke tests cho CI/CD pipeline — Discord Class Bot.
Kiểm tra imports, cấu trúc module, config parsing.
"""
import os
import sys

# Add project to path
_project_dir = os.path.join(os.path.dirname(__file__), "..", "..", "06-lab-complete")
sys.path.insert(0, os.path.abspath(_project_dir))

import importlib


def test_import(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        print(f"  ✅ {module_name} — imports OK")
        return True
    except Exception as e:
        print(f"  ❌ {module_name} — {e}")
        return False


def test_all() -> int:
    passed = 0
    total = 6

    print("=" * 50)
    print("  Discord Class Bot — Smoke Tests")
    print("=" * 50)

    # Test 1-6: verify all modules import correctly
    modules = [
        "bot.config",
        "bot.main",
        "bot.llm",
        "bot.rag",
        "bot.agent",
        "bot.corrections",
    ]

    for mod in modules:
        if test_import(mod):
            passed += 1

    # Verify Settings dataclass works
    print()
    try:
        import os
        os.environ["DISCORD_TOKEN"] = "test-token"
        os.environ["DEEPSEEK_API_KEY"] = "test-key"
        os.environ["TARGET_CHANNEL_IDS"] = "123,456"
        os.environ["INSTRUCTOR_IDS"] = "789"

        # Force reload config module
        if "bot.config" in sys.modules:
            del sys.modules["bot.config"]
        from bot.config import Settings

        s = Settings()
        assert s.discord_token == "test-token"
        assert s.deepseek_api_key == "test-key"
        assert s.target_channel_ids == [123, 456]
        assert s.instructor_ids == ["789"]
        print(f"  ✅ Config parsing — OK")
        passed += 1
        total += 1
    except Exception as e:
        print(f"  ❌ Config parsing — {e}")

    # Clean up env
    for k in ["DISCORD_TOKEN", "DEEPSEEK_API_KEY", "TARGET_CHANNEL_IDS", "INSTRUCTOR_IDS"]:
        os.environ.pop(k, None)

    print(f"\n  Result: {passed}/{total} tests passed")
    if passed == total:
        print("  🎉 All smoke tests passed!")
        return 0
    else:
        print("  ❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(test_all())
