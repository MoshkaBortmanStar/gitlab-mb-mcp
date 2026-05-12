import base64
import json
from mcp.server.fastmcp import FastMCP
from gitlab_mb_mcp.gitlab import GitLabClient

mcp = FastMCP("gitlab-mb-mcp")
gl: GitLabClient | None = None


def _gl() -> GitLabClient:
    global gl
    if gl is None:
        gl = GitLabClient()
    return gl


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


# ── Projects ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_projects(search: str = "", per_page: int = 20) -> str:
    """Search GitLab projects. Returns id, name, path_with_namespace, last_activity_at."""
    data = await _gl().search_projects(search=search, per_page=per_page)
    rows = [
        {"id": p["id"], "path": p["path_with_namespace"],
         "name": p["name"], "last_activity": p.get("last_activity_at", "")}
        for p in data
    ]
    return _json(rows)


@mcp.tool()
async def get_project(project_id: str) -> str:
    """Get project details by id or path (e.g. 'group/repo')."""
    return _json(await _gl().get_project(project_id))


# ── Merge Requests ────────────────────────────────────────────────────────────

@mcp.tool()
async def list_merge_requests(project_id: str, state: str = "opened", per_page: int = 20) -> str:
    """List merge requests. state: opened | closed | merged | all."""
    data = await _gl().list_mrs(project_id, state=state, per_page=per_page)
    rows = [
        {"iid": mr["iid"], "title": mr["title"], "state": mr["state"],
         "author": mr["author"]["username"], "source_branch": mr["source_branch"],
         "target_branch": mr["target_branch"], "web_url": mr["web_url"]}
        for mr in data
    ]
    return _json(rows)


@mcp.tool()
async def get_merge_request(project_id: str, mr_iid: int) -> str:
    """Get full details of a merge request by its IID."""
    return _json(await _gl().get_mr(project_id, mr_iid))


@mcp.tool()
async def get_merge_request_diffs(project_id: str, mr_iid: int) -> str:
    """Get list of changed files (diffs) in a merge request.
    Returns file paths and unified diffs."""
    data = await _gl().get_mr_diffs(project_id, mr_iid)
    result = []
    for d in data:
        result.append({
            "old_path": d.get("old_path"),
            "new_path": d.get("new_path"),
            "new_file": d.get("new_file"),
            "deleted_file": d.get("deleted_file"),
            "renamed_file": d.get("renamed_file"),
            "diff": d.get("diff", ""),
        })
    return _json(result)


@mcp.tool()
async def get_merge_request_commits(project_id: str, mr_iid: int) -> str:
    """Get list of commits included in a merge request."""
    data = await _gl().get_mr_commits(project_id, mr_iid)
    rows = [
        {"id": c["id"][:10], "title": c["title"],
         "author": c["author_name"], "date": c["created_at"]}
        for c in data
    ]
    return _json(rows)


@mcp.tool()
async def get_merge_request_notes(project_id: str, mr_iid: int) -> str:
    """Get all comments (notes) of a merge request."""
    data = await _gl().get_mr_notes(project_id, mr_iid)
    rows = [
        {"id": n["id"], "author": n["author"]["username"],
         "body": n["body"], "created_at": n["created_at"]}
        for n in data
    ]
    return _json(rows)


@mcp.tool()
async def create_merge_request(project_id: str, source_branch: str,
                                target_branch: str, title: str,
                                description: str = "") -> str:
    """Create a new merge request."""
    return _json(await _gl().create_mr(project_id, source_branch, target_branch, title, description))


@mcp.tool()
async def merge_merge_request(project_id: str, mr_iid: int) -> str:
    """Merge an open merge request."""
    return _json(await _gl().merge_mr(project_id, mr_iid))


@mcp.tool()
async def add_merge_request_comment(project_id: str, mr_iid: int, body: str) -> str:
    """Add a comment to a merge request."""
    return _json(await _gl().add_mr_note(project_id, mr_iid, body))


# ── Commits ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_commits(project_id: str, ref: str = "HEAD", per_page: int = 20) -> str:
    """List commits in a project branch/ref."""
    data = await _gl().list_commits(project_id, ref=ref, per_page=per_page)
    rows = [
        {"id": c["id"][:10], "title": c["title"],
         "author": c["author_name"], "date": c["created_at"]}
        for c in data
    ]
    return _json(rows)


@mcp.tool()
async def get_commit(project_id: str, sha: str) -> str:
    """Get commit details by SHA (full or short)."""
    return _json(await _gl().get_commit(project_id, sha))


@mcp.tool()
async def get_commit_diffs(project_id: str, sha: str) -> str:
    """Get file diffs (changes) for a specific commit."""
    data = await _gl().get_commit_diffs(project_id, sha)
    result = []
    for d in data:
        result.append({
            "old_path": d.get("old_path"),
            "new_path": d.get("new_path"),
            "new_file": d.get("new_file"),
            "deleted_file": d.get("deleted_file"),
            "diff": d.get("diff", ""),
        })
    return _json(result)


# ── Files & Tree ──────────────────────────────────────────────────────────────

@mcp.tool()
async def get_file_contents(project_id: str, file_path: str, ref: str = "HEAD") -> str:
    """Get file contents from the repository at a given ref (branch/tag/commit SHA).
    file_path example: 'src/main.py'"""
    data = await _gl().get_file(project_id, file_path, ref=ref)
    content_b64 = data.get("content", "")
    encoding = data.get("encoding", "base64")
    if encoding == "base64":
        content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    else:
        content = content_b64
    return content


@mcp.tool()
async def list_repository_tree(project_id: str, path: str = "",
                                ref: str = "HEAD", recursive: bool = False) -> str:
    """List files and directories in the repository.
    path: subdirectory to list (empty = root). recursive: expand all subdirs."""
    data = await _gl().list_tree(project_id, path=path, ref=ref, recursive=recursive)
    rows = [{"type": n["type"], "path": n["path"], "name": n["name"]} for n in data]
    return _json(rows)


# ── Issues ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_issues(project_id: str, state: str = "opened", per_page: int = 20) -> str:
    """List project issues. state: opened | closed | all."""
    data = await _gl().list_issues(project_id, state=state, per_page=per_page)
    rows = [
        {"iid": i["iid"], "title": i["title"], "state": i["state"],
         "author": i["author"]["username"], "web_url": i["web_url"]}
        for i in data
    ]
    return _json(rows)


@mcp.tool()
async def get_issue(project_id: str, issue_iid: int) -> str:
    """Get full details of an issue by its IID."""
    return _json(await _gl().get_issue(project_id, issue_iid))


@mcp.tool()
async def create_issue(project_id: str, title: str, description: str = "") -> str:
    """Create a new issue in the project."""
    return _json(await _gl().create_issue(project_id, title, description))


@mcp.tool()
async def add_issue_comment(project_id: str, issue_iid: int, body: str) -> str:
    """Add a comment to an issue."""
    return _json(await _gl().add_issue_note(project_id, issue_iid, body))


# ── Branches ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_branches(project_id: str, search: str = "") -> str:
    """List repository branches. Optionally filter by search string."""
    data = await _gl().list_branches(project_id, search=search)
    rows = [
        {"name": b["name"], "commit_sha": b["commit"]["id"][:10],
         "protected": b.get("protected", False)}
        for b in data
    ]
    return _json(rows)


@mcp.tool()
async def create_branch(project_id: str, branch: str, ref: str) -> str:
    """Create a new branch from an existing ref (branch/tag/SHA)."""
    return _json(await _gl().create_branch(project_id, branch, ref))


# ── Pipelines ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_pipelines(project_id: str, ref: str = "", per_page: int = 20) -> str:
    """List CI/CD pipelines. Optionally filter by ref (branch/tag)."""
    data = await _gl().list_pipelines(project_id, ref=ref, per_page=per_page)
    rows = [
        {"id": p["id"], "status": p["status"], "ref": p["ref"],
         "sha": p["sha"][:10], "created_at": p["created_at"]}
        for p in data
    ]
    return _json(rows)


@mcp.tool()
async def get_pipeline(project_id: str, pipeline_id: int) -> str:
    """Get details of a specific pipeline."""
    return _json(await _gl().get_pipeline(project_id, pipeline_id))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
