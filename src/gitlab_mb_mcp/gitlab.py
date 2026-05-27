import os
import httpx
from typing import Any


class GitLabClient:
    def __init__(self):
        self.base_url = os.environ["GITLAB_API_URL"].rstrip("/")
        self.token = os.environ["GITLAB_PERSONAL_ACCESS_TOKEN"]
        self._client = httpx.AsyncClient(
            headers={"PRIVATE-TOKEN": self.token},
            timeout=30.0,
            verify=False,
        )

    async def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        r = await self._client.get(url, params=params)
        r.raise_for_status()
        return r.json()

    async def post(self, path: str, json: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        r = await self._client.post(url, json=json)
        r.raise_for_status()
        return r.json()

    async def put(self, path: str, json: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        r = await self._client.put(url, json=json)
        r.raise_for_status()
        return r.json()

    # ── Projects ──────────────────────────────────────────────────────────────

    async def search_projects(self, search: str = "", per_page: int = 20) -> list:
        return await self.get("/projects", {"search": search, "per_page": per_page, "order_by": "last_activity_at"})

    async def get_project(self, project_id: str) -> dict:
        return await self.get(f"/projects/{_enc(project_id)}")

    # ── Merge Requests ────────────────────────────────────────────────────────

    async def list_mrs(self, project_id: str, state: str = "opened", per_page: int = 20) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/merge_requests", {"state": state, "per_page": per_page})

    async def get_mr(self, project_id: str, mr_iid: int) -> dict:
        return await self.get(f"/projects/{_enc(project_id)}/merge_requests/{mr_iid}")

    async def get_mr_diffs(self, project_id: str, mr_iid: int) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/merge_requests/{mr_iid}/diffs", {"per_page": 100})

    async def get_mr_commits(self, project_id: str, mr_iid: int) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/merge_requests/{mr_iid}/commits")

    async def create_mr(self, project_id: str, source_branch: str, target_branch: str,
                        title: str, description: str = "") -> dict:
        return await self.post(f"/projects/{_enc(project_id)}/merge_requests", {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
        })

    async def merge_mr(self, project_id: str, mr_iid: int) -> dict:
        return await self.put(f"/projects/{_enc(project_id)}/merge_requests/{mr_iid}/merge")

    async def add_mr_note(self, project_id: str, mr_iid: int, body: str) -> dict:
        return await self.post(f"/projects/{_enc(project_id)}/merge_requests/{mr_iid}/notes", {"body": body})

    async def get_mr_notes(self, project_id: str, mr_iid: int) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/merge_requests/{mr_iid}/notes")

    # ── Commits ───────────────────────────────────────────────────────────────

    async def list_commits(self, project_id: str, ref: str = "HEAD", per_page: int = 20) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/repository/commits",
                              {"ref_name": ref, "per_page": per_page})

    async def get_commit(self, project_id: str, sha: str) -> dict:
        return await self.get(f"/projects/{_enc(project_id)}/repository/commits/{sha}")

    async def get_commit_diffs(self, project_id: str, sha: str) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/repository/commits/{sha}/diff")

    # ── Files & Tree ──────────────────────────────────────────────────────────

    async def get_file(self, project_id: str, file_path: str, ref: str = "HEAD") -> dict:
        enc_path = file_path.replace("/", "%2F")
        return await self.get(f"/projects/{_enc(project_id)}/repository/files/{enc_path}",
                              {"ref": ref})

    async def list_tree(self, project_id: str, path: str = "", ref: str = "HEAD",
                        recursive: bool = False) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/repository/tree",
                              {"path": path, "ref": ref, "recursive": recursive, "per_page": 100})

    # ── Issues ────────────────────────────────────────────────────────────────

    async def list_issues(self, project_id: str, state: str = "opened", per_page: int = 20) -> list:
        return await self.get(f"/projects/{_enc(project_id)}/issues",
                              {"state": state, "per_page": per_page})

    async def get_issue(self, project_id: str, issue_iid: int) -> dict:
        return await self.get(f"/projects/{_enc(project_id)}/issues/{issue_iid}")

    async def create_issue(self, project_id: str, title: str, description: str = "") -> dict:
        return await self.post(f"/projects/{_enc(project_id)}/issues",
                               {"title": title, "description": description})

    async def add_issue_note(self, project_id: str, issue_iid: int, body: str) -> dict:
        return await self.post(f"/projects/{_enc(project_id)}/issues/{issue_iid}/notes",
                               {"body": body})

    # ── Branches ──────────────────────────────────────────────────────────────

    async def list_branches(self, project_id: str, search: str = "") -> list:
        params: dict = {"per_page": 50}
        if search:
            params["search"] = search
        return await self.get(f"/projects/{_enc(project_id)}/repository/branches", params)

    async def create_branch(self, project_id: str, branch: str, ref: str) -> dict:
        return await self.post(f"/projects/{_enc(project_id)}/repository/branches",
                               {"branch": branch, "ref": ref})

    # ── Pipelines ─────────────────────────────────────────────────────────────

    async def list_pipelines(self, project_id: str, ref: str = "", per_page: int = 20) -> list:
        params: dict = {"per_page": per_page}
        if ref:
            params["ref"] = ref
        return await self.get(f"/projects/{_enc(project_id)}/pipelines", params)

    async def get_pipeline(self, project_id: str, pipeline_id: int) -> dict:
        return await self.get(f"/projects/{_enc(project_id)}/pipelines/{pipeline_id}")

    async def aclose(self):
        await self._client.aclose()


def _enc(project_id: str) -> str:
    return project_id.replace("/", "%2F")
