"""Container entrypoint: launch the official Codex CLI, without host config."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    gateway = os.environ['BENCH_GATEWAY']
    config = f'''model = "{os.environ['BENCH_MODEL']}"
model_provider = "nju_bench"
model_catalog_json = "/runtime/model_catalog.json"
approval_policy = "never"
web_search = "disabled"
[model_providers.nju_bench]
name = "NJU benchmark gateway"
base_url = "{gateway}/v1"
env_key = "BENCH_LOCAL_TOKEN"
wire_api = "responses"
supports_websockets = false
[mcp_servers.fixed_media]
command = "python"
args = ["/runtime/media_mcp.py"]
env_vars = ["BENCH_GATEWAY", "BENCH_LOCAL_TOKEN"]
startup_timeout_sec = 30
tool_timeout_sec = 210
'''
    # Container-local empty home; never loads the host user's Codex files.
    if os.environ.get('BENCH_REASONING_EFFORT'):
        effort = os.environ['BENCH_REASONING_EFFORT']
        if effort not in ['low','medium','high','xhigh','max']:
            raise ValueError('Invalid explicit reasoning effort')
        config = f'model_reasoning_effort = "{effort}"\n' + config
    persist = os.environ.get('BENCH_PERSIST_SESSION') == '1'
    home = Path('/workspace/scratch/.codex-home' if persist else '/tmp/codex-home')
    os.environ['CODEX_HOME'] = str(home)
    os.environ['HOME'] = '/tmp'
    home.mkdir(parents=True, exist_ok=True)
    (home / 'config.toml').write_text(config, encoding='utf-8')
    prompt = Path('/runtime/prompt.txt').read_text(encoding='utf-8')
    argv = ['/opt/codex', 'exec', '--skip-git-repo-check', '--ephemeral', '--json',
            '--color', 'never', '--dangerously-bypass-approvals-and-sandbox',
            '--cd', '/workspace', '--model', os.environ['BENCH_MODEL'],
            '--output-last-message', '/workspace/scratch/codex_final_message.txt', '-']
    if persist:
        argv.remove('--ephemeral')
    if os.environ.get('BENCH_RESUME_THREAD'):
        argv = ['/opt/codex', 'exec', 'resume', '--skip-git-repo-check', '--json',
                '--dangerously-bypass-approvals-and-sandbox', '--model', os.environ['BENCH_MODEL'],
                '--output-last-message', '/workspace/scratch/codex_final_message.txt',
                os.environ['BENCH_RESUME_THREAD'], '-']
    # Bypass is ONLY inside the externally isolated read-only-root container.
    return subprocess.run(argv, input=prompt.encode('utf-8')).returncode


if __name__ == '__main__':
    sys.exit(main())
