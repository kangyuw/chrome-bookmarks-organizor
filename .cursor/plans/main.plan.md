## 🛠️ Project: AI-Powered Bookmark Architect

**Goal:** Transform a messy `bookmarks.html` into a structured, semantic, and enriched library using an incremental approach.

---

### 1. Data Architecture & Parsing

Chrome bookmarks use the **Netscape-Bookmark file format**. It is not standard HTML and can be tricky to parse.

- **Parser Choice:** Use `BeautifulSoup` with the `lxml` or `html.parser` feature.
- **Data Extraction:**
- Iterate through `<DT>` and `<A>` tags.
- Capture: `HREF` (URL), `Title`, `ADD_DATE`, and the **Folder Path** (the chain of `<H3>` headers preceding the link).

- **Deduplication:**
- Implement a `set()` or `dict()` to store unique URLs.
- **Logic:** If a URL is exact, keep the one with the most recent `ADD_DATE`.

### 2. The "Pre-flight" Crawler (Performance Layer)

To handle thousands of URLs without stalling, you must use **Asynchronous I/O**.

- **Framework:** `asyncio` + `aiohttp`.
- **Validation Logic:**
- Perform a `HEAD` request first (faster than `GET`).
- **Broken Link Filter:** If the status is `404` or `410`, mark for deletion.

- **Enrichment Logic:** * If the title is ambiguous (e.g., "Home", "Welcome", or just a domain), perform a `GET` request.
- Extract the `<meta name="description">` or `<title>` from the page source to provide Gemini with better context.

- **Concurrency Control:** Use a `Semaphore` (e.g., `asyncio.Semaphore(20)`) to avoid being blocked by websites or overwhelming your OS.

### 3. Gemini API Orchestration

This is where the semantic "Self-Adaptive Hierarchy" happens.

- **Batching Strategy:** * Do not send 3,000 items at once. Send batches of **50–80 items** per prompt.
- Use the **Gemini 1.5 Flash** model for cost-efficiency and high speed for classification tasks.

- **Prompt Engineering (System Instruction):**
> "You are a professional Information Architect. You will receive a JSON list of bookmarks (Title, URL, Original Folder, Snippet).
> **Your Tasks:**
> 1. Assign each to a semantic 'Category Path' (e.g., ['Tech', 'Coding', 'Python']).
> 2. Use a **Dynamic Depth**: Create sub-folders only if there are >10 related items.
> 3. Generate a **30-word Chinese description** for each.
> 4. **Identify Series:** If multiple URLs belong to the same series/site (e.g., a blog series), group them together.
> 5. Return strictly valid JSON."
>
>

- **Structured Output:** Use the `response_mime_type: "application/json"` setting in the Gemini API to ensure the output maps directly to your local objects.

### 4. Incremental Generator (The Output)

To ensure safety, we produce an **Incremental File**.

- **Output Format:** Netscape HTML.
- **Wrapper:** Wrap all AI-processed content inside a single root folder: `<H3>AI Optimized [Date]</H3>`.
- **DD Tag Integration:** Place the 30-word summary inside the `<DD>` tag immediately following the `<DT><A>...</A>` tag. This is the official (though often hidden) standard for bookmark notes.

### 5. Execution Roadmap (Development Phases)

| Phase | Milestone | Key Task |
| --- | --- | --- |
| **Phase 1** | **Ingestion** | Build the `html_to_json` parser; verify original folder paths are preserved. |
| **Phase 2** | **Cleanup** | Run the `async` 404-checker; remove duplicates; save a "cleaned" JSON. |
| **Phase 3** | **Classification** | Implement the Batch API caller; test Prompt with 1 batch to verify folder logic. |
| **Phase 4** | **Reconstruction** | Build the `json_to_html` writer with recursive folder creation. |