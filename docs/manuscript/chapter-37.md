---
title: "Chapter 37: Cross-Stack Essentials - Go, TypeScript, Angular & Transferable AI Patterns"
---

# Chapter 37: Cross-Stack Essentials - Go, TypeScript, Angular & Transferable AI Patterns

## Introduction

Modern senior and lead roles increasingly require versatility across the stack. While you may be Python-first, understanding Go for backend services, TypeScript and Angular for enterprise frontend delivery, and transferable AI workflow patterns positions you as a stronger technical leader. This chapter covers the essentials you need to collaborate effectively across backend, frontend, and platform teams building production systems for international clients.

---

## 1. Go Essentials for Python Developers

### 1.1 Why Go Matters for Backend Engineers

**Key Differences from Python:**
- **Compiled, statically typed** (vs Python's interpreted, dynamic typing)
- **Built-in concurrency** (goroutines vs Python's asyncio/threading)
- **Memory efficient** for high-throughput services
- **Fast compilation** and single binary deployment

**When Teams Choose Go:**
- High-performance microservices
- CLI tools and SDKs
- Systems programming
- Network services requiring high concurrency

### 1.2 Go Syntax Basics - Quick Reference

#### Variable Declaration
**Python:**
```python
name = "Alice"
age = 30
```

**Go:**
```go
// Multiple ways
var name string = "Alice"
age := 30  // Type inference
const MaxRetries = 3
```

#### Functions
**Python:**
```python
def add(a: int, b: int) -> int:
    return a + b
```

**Go:**
```go
// Multiple return values common
func add(a int, b int) int {
    return a + b
}

// Error handling pattern
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}
```

#### Structs (Similar to Python dataclasses)
**Python:**
```python
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str
```

**Go:**
```go
type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

// Method on struct
func (u *User) FullInfo() string {
    return fmt.Sprintf("%s (%s)", u.Name, u.Email)
}
```

#### Interfaces (Duck typing made explicit)
```go
// Python - Implicit protocol
class PaymentProcessor:
    def process(self, amount: float) -> bool:
        pass

// Go - Explicit interface
type PaymentProcessor interface {
    Process(amount float64) bool
}

type StripeProcessor struct{}

func (s *StripeProcessor) Process(amount float64) bool {
    // Implementation
    return true
}
```

### 1.3 Concurrency - Goroutines vs Python AsyncIO

**Python AsyncIO:**
```python
import asyncio

async def fetch_data(url: str) -> dict:
    # async HTTP call
    return data

async def main():
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

**Go Goroutines:**
```go
func fetchData(url string, ch chan<- map[string]interface{}) {
    // Make HTTP call
    ch <- data
}

func main() {
    ch := make(chan map[string]interface{})
    
    for _, url := range urls {
        go fetchData(url, ch)  // Launch goroutine
    }
    
    for i := 0; i < len(urls); i++ {
        result := <-ch  // Receive from channel
    }
}
```

**Key Concept - Channels:**
```go
// Unbuffered channel (blocking)
ch := make(chan int)

// Buffered channel
ch := make(chan int, 100)

// Send and receive
ch <- 42        // Send
value := <-ch   // Receive

// Select for multiple channels (like asyncio.wait)
select {
case msg := <-ch1:
    fmt.Println("Received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("Received from ch2:", msg)
case <-time.After(1 * time.Second):
    fmt.Println("Timeout")
}
```

### 1.4 Error Handling - No Exceptions

**Python:**
```python
try:
    result = risky_operation()
except ValueError as e:
    handle_error(e)
```

**Go - Explicit error returns:**
```go
result, err := riskyOperation()
if err != nil {
    // Handle error
    return err
}
// Use result
```

**Idiomatic Error Wrapping:**
```go
import "fmt"

func processFile(path string) error {
    data, err := os.ReadFile(path)
    if err != nil {
        return fmt.Errorf("failed to read file %s: %w", path, err)
    }
    // Process data
    return nil
}
```

### 1.5 Building a Simple REST API - Go vs Python

**Python (FastAPI):**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

@app.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

@app.post("/users")
async def create_user(user: User) -> User:
    return db.create_user(user)
```

**Go (using gin framework):**
```go
package main

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

func main() {
    r := gin.Default()
    
    r.GET("/users/:user_id", func(c *gin.Context) {
        userID := c.Param("user_id")
        user, err := db.GetUser(userID)
        if err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "user not found"})
            return
        }
        c.JSON(http.StatusOK, user)
    })
    
    r.POST("/users", func(c *gin.Context) {
        var user User
        if err := c.ShouldBindJSON(&user); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        db.CreateUser(user)
        c.JSON(http.StatusCreated, user)
    })
    
    r.Run(":8080")
}
```

### 1.6 Key Go Patterns for Microservices

**Context Propagation (Critical for distributed systems):**
```go
import "context"

func fetchUserWithTimeout(ctx context.Context, userID string) (*User, error) {
    ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()
    
    // Pass context to downstream calls
    user, err := userService.Get(ctx, userID)
    if err != nil {
        return nil, err
    }
    return user, nil
}
```

**Graceful Shutdown:**
```go
func main() {
    srv := &http.Server{Addr: ":8080"}
    
    go func() {
        if err := srv.ListenAndServe(); err != nil {
            log.Fatal(err)
        }
    }()
    
    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    // Graceful shutdown with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal("Server forced to shutdown:", err)
    }
}
```

### 1.7 Testing in Go

**Python (pytest):**
```python
def test_add_numbers():
    assert add(2, 3) == 5

@pytest.fixture
def sample_user():
    return User(id=1, name="Test")
```

**Go (testing package):**
```go
import "testing"

func TestAddNumbers(t *testing.T) {
    result := add(2, 3)
    if result != 5 {
        t.Errorf("Expected 5, got %d", result)
    }
}

// Table-driven tests (idiomatic Go)
func TestDivide(t *testing.T) {
    tests := []struct {
        name    string
        a, b    float64
        want    float64
        wantErr bool
    }{
        {"valid", 10, 2, 5, false},
        {"zero divisor", 10, 0, 0, true},
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := divide(tt.a, tt.b)
            if (err != nil) != tt.wantErr {
                t.Errorf("unexpected error: %v", err)
            }
            if got != tt.want {
                t.Errorf("got %v, want %v", got, tt.want)
            }
        })
    }
}
```

### 1.8 Go for Python Developers - Quick Reference

| Concept | Python | Go |
|---------|--------|-----|
| **Package Management** | `pip install requests` | `go get github.com/...` |
| **Virtual Envs** | `venv`, `virtualenv` | Go modules (go.mod) - no venv needed |
| **Formatting** | `black`, `ruff` | `go fmt` (built-in, enforced) |
| **Linting** | `pylint`, `mypy` | `go vet`, `golangci-lint` |
| **Dependency Injection** | Manual or frameworks | Interfaces + constructors |
| **ORM** | SQLAlchemy, Django ORM | GORM, sqlx (less magic) |
| **JSON** | `json.loads()` / `json.dumps()` | `json.Marshal()` / `json.Unmarshal()` |
| **Null handling** | `None`, `Optional[T]` | `nil`, pointers `*T` |

**Interview Talking Points:**
- "While I'm Python-first, I understand Go's value for high-performance services and have built [X] in Go"
- "I can read Go codebases effectively and contribute to Go microservices"
- "I appreciate Go's explicit error handling and built-in concurrency primitives"

---

## 2. TypeScript & Angular Fundamentals for Backend Leads

### 2.1 Why Backend Engineers Need Angular and TypeScript Knowledge

You do not need to be a dedicated frontend specialist to succeed in full-stack lead roles. You do need to understand how enterprise frontend teams structure applications, consume APIs, manage state, and debug distributed user-facing issues.

Angular and TypeScript matter because they emphasize:

- strong project conventions for larger teams
- dependency injection and modular architecture
- explicit typing across UI models and API contracts
- reactive programming with RxJS
- testable forms, routing, and state transitions

For European client projects and long-lived business applications, these properties often matter more than raw frontend experimentation speed.

### 2.2 TypeScript Core Concepts for Python Engineers

TypeScript plays a role similar to adding stricter contracts on top of JavaScript. If Python typing helps you maintain large backend codebases, TypeScript does the same for frontend applications.

#### Interfaces and Type Aliases
```ts
interface UserSummary {
    id: number;
    name: string;
    email: string;
    createdAt: string;
}

type ApiResult<T> = {
    data: T;
    requestId: string;
    errors?: Record<string, string[]>;
};
```

**Python Parallel:**
```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class UserSummary(BaseModel):
    id: int
    name: str
    email: str
    created_at: str

class ApiResult(BaseModel, Generic[T]):
    data: T
    request_id: str
```

#### Union Types and Narrowing
```ts
type LoadState<T> =
    | { status: "idle" }
    | { status: "loading" }
    | { status: "success"; data: T }
    | { status: "error"; message: string };

function renderState(state: LoadState<UserSummary[]>) {
    if (state.status === "success") {
        return state.data.length;
    }
    return 0;
}
```

**Why it matters:** TypeScript helps frontend teams model UI state explicitly instead of relying on loose booleans and nullable values.

#### Generics and Strict Null Handling
```ts
function getById<T extends { id: number }>(items: T[], id: number): T | undefined {
    return items.find(item => item.id === id);
}
```

**Interview talking point:** strict typing reduces regression risk during refactors and makes backend/frontend contracts easier to maintain over time.

### 2.3 Angular Architecture in 15 Minutes

Angular applications are typically organized around a few core building blocks:

- **Components**: render UI and handle user interaction
- **Services**: own API calls and reusable business logic
- **Dependency Injection**: wires services into components cleanly
- **Routing**: defines page transitions and route guards
- **Interceptors**: centralize auth headers, tracing, and common error handling
- **Reactive Forms**: model complex form behavior with explicit validation

#### Component + Service Pattern
```ts
// user.service.ts
@Injectable({ providedIn: 'root' })
export class UserService {
    constructor(private http: HttpClient) {}

    getUser(userId: number): Observable<UserSummary> {
        return this.http.get<UserSummary>(`/api/users/${userId}`);
    }
}

// user-profile.component.ts
@Component({
    selector: 'app-user-profile',
    template: `<h2 *ngIf="user$ | async as user">{{ user.name }}</h2>`
})
export class UserProfileComponent {
    user$ = this.userService.getUser(42);

    constructor(private userService: UserService) {}
}
```

**Backend parallel:** services are close to application service classes; components are closer to thin controllers or templates.

#### Routing and Guards
```ts
const routes: Routes = [
    {
        path: 'admin',
        component: AdminDashboardComponent,
        canActivate: [AuthGuard, RoleGuard]
    }
];
```

**Important:** guards improve UX, but backend authorization must still be enforced in Django/DRF.

### 2.4 How Angular Consumes Django/DRF APIs

**What your backend sends:**
```python
@api_view(["GET"])
def get_user(request, user_id: int):
    return Response({
        "id": user_id,
        "name": "Alice",
        "email": "alice@example.com",
        "created_at": "2024-01-15T10:30:00Z"
    })
```

**How Angular consumes it:**
```ts
interface UserResponse {
    id: number;
    name: string;
    email: string;
    created_at: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
    constructor(private http: HttpClient) {}

    getUser(userId: number): Observable<UserResponse> {
        return this.http.get<UserResponse>(`/api/users/${userId}`);
    }
}
```

This is where full-stack leadership matters: the frontend becomes much easier to maintain when your API contracts are stable, typed, paginated, and consistent.

### 2.5 API Design Patterns Angular Teams Love

#### Prefer Stable Response Envelopes for Complex Screens
```python
@api_view(["GET"])
def get_project_dashboard(request, project_id: int):
    return Response({
        "project": {...},
        "recent_activity": [...],
        "assigned_users": [...],
        "open_issues_count": 14
    })
```

This reduces chatty frontend orchestration for dashboard-style screens.

#### Use Predictable Pagination Shapes
```python
@api_view(["GET"])
def list_users(request):
    return Response({
        "count": 245,
        "next": "/api/users?page=3",
        "previous": "/api/users?page=1",
        "results": [...]
    })
```

Angular teams can map this directly into tables, filters, and infinite scroll patterns.

#### Return Structured Validation Errors
```python
return Response(
    {
        "errors": {
            "email": ["Email already exists"],
            "name": ["Name must be at least 2 characters"]
        }
    },
    status=400,
)
```

Reactive forms become much easier to manage when backend validation errors are machine-readable and field-specific.

### 2.6 RxJS Patterns Backend Leads Should Understand

RxJS is central to Angular because it models time-based and async behavior explicitly.

#### Common Operators
- `map`: transform response data
- `switchMap`: cancel stale in-flight requests when new input arrives
- `catchError`: convert failures into controlled UI states
- `debounceTime`: delay reactions to noisy inputs like search boxes

#### Search Example
```ts
this.searchResults$ = this.searchControl.valueChanges.pipe(
    debounceTime(250),
    distinctUntilChanged(),
    switchMap(query =>
        this.http.get<SearchResult[]>('/api/search', { params: { q: query } })
    ),
    catchError(() => of([]))
);
```

**Backend impact:** APIs for search and filtering must support low-latency repeated calls, sensible query parameters, and predictable empty/error responses.

### 2.7 Forms, Authentication, and Error Handling

Reactive forms are the Angular default for complex enterprise workflows.

```ts
this.userForm = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
});
```

#### Auth Integration Pattern
- Angular interceptor attaches access token
- backend validates token and permissions
- `401` means unauthenticated
- `403` means authenticated but forbidden
- frontend redirects or shows role-based UI state

#### Interceptor Example
```ts
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
    intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        const token = localStorage.getItem('access_token');
        const authReq = token
            ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
            : req;

        return next.handle(authReq);
    }
}
```

**Backend checklist:**
- consistent auth error codes
- refresh-token strategy if used
- CSRF strategy for session-based auth
- audit logging for privileged actions

### 2.8 Frontend Architecture and Team-Scale Delivery

Lead-level full-stack interviews often test whether you can keep frontend complexity under control, not whether you can write every component from memory.

Good architectural habits:

- organize by feature, not by file type alone
- isolate API access in services
- keep presentation components thin
- centralize auth, tracing, and error handling in interceptors
- avoid unbounded shared global state
- use typed domain models shared across critical flows

#### Example Feature Structure
```text
src/app/
  features/
    users/
      pages/
      components/
      services/
      models/
      users.routes.ts
  shared/
    interceptors/
    guards/
    ui/
```

**Lead signal:** explain how this structure improves onboarding, ownership boundaries, and testability.

### 2.9 Angular Interview Talking Points for Backend Leads

When asked about frontend experience:

- "I am strongest on backend architecture, but I understand Angular's enterprise patterns: components, services, DI, routing, interceptors, and reactive forms."
- "I design APIs so Angular teams can move quickly: stable contracts, field-level validation errors, pagination, filtering, and clear auth behavior."
- "I understand RxJS well enough to reason about debounced search, request cancellation, and async UI flows."
- "I can collaborate effectively on full-stack delivery even when the backend is my primary strength."

What you do not need to fake:

- deep CSS framework expertise
- advanced animation systems
- niche build-pipeline internals
- cutting-edge frontend library comparisons

---

## 3. Transferable Gen AI Workflow Patterns

### 3.1 Core Agentic Patterns Across Platforms

These patterns work regardless of whether you use LangChain, LlamaIndex, Semantic Kernel, or custom implementations.

#### Pattern 1: ReAct (Reasoning + Acting)
**Concept:** Agent reasons about next action, takes action, observes result, repeats.

**Platform-Agnostic Flow:**
```
1. User Input → Agent
2. Agent Thinks: "What do I need to do?"
3. Agent Selects Tool: "I'll search the database"
4. Agent Executes Tool
5. Agent Observes Result
6. Agent Decides: "Need more info" or "Can answer now"
7. Repeat or Respond
```

**LangChain Implementation:**
```python
from langchain.agents import create_react_agent
from langchain.tools import Tool

tools = [
    Tool(name="Search", func=search_database),
    Tool(name="Calculate", func=calculator)
]

agent = create_react_agent(llm, tools, prompt_template)
agent.invoke({"input": "What's the revenue for Q4?"})
```

**Custom Implementation (Framework-Agnostic):**
```python
class ReActAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
    
    def run(self, query: str, max_iterations: int = 5):
        history = []
        
        for i in range(max_iterations):
            # Thought step
            thought = self.llm.generate(
                f"Query: {query}\nHistory: {history}\nThought:"
            )
            
            # Action step
            if "Final Answer:" in thought:
                return self.extract_answer(thought)
            
            action, action_input = self.parse_action(thought)
            
            # Execute tool
            observation = self.tools[action].run(action_input)
            
            history.append({
                "thought": thought,
                "action": action,
                "observation": observation
            })
        
        return "Max iterations reached"
```

**Azure OpenAI Version:**
```python
from openai import AzureOpenAI

class AzureReActAgent:
    def __init__(self, azure_client, tools):
        self.client = azure_client
        self.tools = tools
    
    def run(self, query: str):
        messages = [{"role": "user", "content": query}]
        
        while True:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                functions=[tool.schema for tool in self.tools],
                function_call="auto"
            )
            
            message = response.choices[0].message
            
            if message.function_call:
                # Execute function
                tool_name = message.function_call.name
                tool_args = json.loads(message.function_call.arguments)
                result = self.execute_tool(tool_name, tool_args)
                
                messages.append({
                    "role": "function",
                    "name": tool_name,
                    "content": str(result)
                })
            else:
                return message.content
```

#### Pattern 2: Chain of Thought (CoT)
**Concept:** Break complex tasks into step-by-step reasoning.

**Platform-Agnostic Prompt Pattern:**
```python
def chain_of_thought_prompt(query: str) -> str:
    return f"""
Let's solve this step by step:

Question: {query}

Step 1: Understand the problem
[Your analysis]

Step 2: Identify what information we need
[List requirements]

Step 3: Gather that information
[Actions]

Step 4: Synthesize the answer
[Final answer]
"""

# Works with any LLM API
response = llm.generate(chain_of_thought_prompt(user_query))
```

**Implementation with Any LLM:**
```python
class CoTAgent:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def solve(self, problem: str) -> dict:
        steps = []
        
        # Step 1: Problem decomposition
        decomp = await self.llm.generate(
            f"Break this into steps: {problem}"
        )
        steps.append({"stage": "decomposition", "output": decomp})
        
        # Step 2: Execute each step
        for step in self.parse_steps(decomp):
            result = await self.llm.generate(
                f"Solve: {step}\nPrevious context: {steps}"
            )
            steps.append({"stage": step, "output": result})
        
        # Step 3: Synthesis
        final = await self.llm.generate(
            f"Synthesize answer from: {steps}"
        )
        
        return {
            "answer": final,
            "reasoning_chain": steps
        }
```

#### Pattern 3: RAG (Retrieval-Augmented Generation)
**Concept:** Retrieve relevant context, augment prompt, generate answer.

**Universal RAG Architecture:**
```
User Query → Embedding → Vector Search → Retrieved Docs → 
LLM (Query + Context) → Answer
```

**Framework-Agnostic Implementation:**
```python
from typing import List, Dict

class UniversalRAG:
    def __init__(self, embedding_model, vector_store, llm):
        self.embedder = embedding_model
        self.vector_store = vector_store
        self.llm = llm
    
    async def query(self, question: str, top_k: int = 5) -> str:
        # 1. Embed query
        query_embedding = await self.embedder.embed(question)
        
        # 2. Retrieve relevant documents
        docs = await self.vector_store.similarity_search(
            query_embedding, 
            top_k=top_k
        )
        
        # 3. Build augmented prompt
        context = "\n\n".join([doc.content for doc in docs])
        augmented_prompt = f"""
Context information:
{context}

Question: {question}

Answer based on the context above:
"""
        
        # 4. Generate answer
        answer = await self.llm.generate(augmented_prompt)
        
        return {
            "answer": answer,
            "sources": [doc.metadata for doc in docs]
        }
```

**Works with Any Vector DB:**
```python
# Pinecone
class PineconeVectorStore:
    def similarity_search(self, embedding, top_k):
        return self.index.query(embedding, top_k=top_k)

# Weaviate
class WeaviateVectorStore:
    def similarity_search(self, embedding, top_k):
        return self.client.query.get(...).with_near_vector(embedding).with_limit(top_k).do()

# PostgreSQL with pgvector
class PgVectorStore:
    def similarity_search(self, embedding, top_k):
        return self.db.execute(
            "SELECT * FROM docs ORDER BY embedding <-> %s LIMIT %s",
            (embedding, top_k)
        )
```

#### Pattern 4: Multi-Agent Orchestration
**Concept:** Multiple specialized agents collaborate to solve complex tasks.

**Universal Multi-Agent Pattern:**
```python
class Agent:
    def __init__(self, name: str, role: str, llm, tools):
        self.name = name
        self.role = role
        self.llm = llm
        self.tools = tools
    
    async def act(self, task: str, context: dict) -> dict:
        prompt = f"""
Role: {self.role}
Task: {task}
Context: {context}

What action should I take?
"""
        action = await self.llm.generate(prompt)
        result = await self.execute_action(action)
        return result

class Orchestrator:
    def __init__(self, agents: List[Agent]):
        self.agents = {agent.name: agent for agent in agents}
    
    async def solve(self, problem: str) -> dict:
        # Decompose problem
        plan = await self.create_plan(problem)
        
        # Execute plan with agents
        results = {}
        for step in plan:
            agent = self.agents[step['agent']]
            result = await agent.act(step['task'], results)
            results[step['id']] = result
        
        # Synthesize results
        return await self.synthesize(results)
```

**Example - Content Creation Pipeline:**
```python
# Define specialized agents
researcher = Agent(
    name="researcher",
    role="Research and gather information",
    llm=llm,
    tools=[web_search, database_query]
)

writer = Agent(
    name="writer",
    role="Create engaging content",
    llm=llm,
    tools=[generate_text, format_markdown]
)

reviewer = Agent(
    name="reviewer",
    role="Review and improve content",
    llm=llm,
    tools=[check_grammar, verify_facts]
)

# Orchestrate workflow
orchestrator = Orchestrator([researcher, writer, reviewer])

result = await orchestrator.solve(
    "Create a blog post about AI agents in production"
)
```

### 3.2 Workflow Patterns - Platform-Agnostic

#### Sequential Workflow
```python
class SequentialWorkflow:
    def __init__(self, steps: List[Callable]):
        self.steps = steps
    
    async def execute(self, input_data: dict) -> dict:
        context = input_data
        
        for step in self.steps:
            result = await step(context)
            context.update(result)
        
        return context

# Usage
workflow = SequentialWorkflow([
    extract_requirements,
    generate_design,
    implement_code,
    run_tests,
    deploy
])

await workflow.execute({"project_spec": "Build user auth"})
```

#### Branching Workflow (Conditional)
```python
class BranchingWorkflow:
    def __init__(self, decision_fn: Callable):
        self.decision_fn = decision_fn
        self.branches = {}
    
    def add_branch(self, condition: str, workflow: Callable):
        self.branches[condition] = workflow
    
    async def execute(self, input_data: dict) -> dict:
        decision = await self.decision_fn(input_data)
        workflow = self.branches[decision]
        return await workflow(input_data)

# Usage
workflow = BranchingWorkflow(
    decision_fn=lambda ctx: classify_query(ctx['query'])
)

workflow.add_branch('code_question', code_assistant_workflow)
workflow.add_branch('general_question', general_qa_workflow)
workflow.add_branch('creative', creative_writing_workflow)
```

#### Parallel Workflow
```python
import asyncio

class ParallelWorkflow:
    def __init__(self, tasks: List[Callable]):
        self.tasks = tasks
    
    async def execute(self, input_data: dict) -> List[dict]:
        results = await asyncio.gather(*[
            task(input_data) for task in self.tasks
        ])
        return results

# Usage - Multiple AI models for consensus
workflow = ParallelWorkflow([
    gpt4_analysis,
    claude_analysis,
    gemini_analysis
])

results = await workflow.execute({"document": doc})
consensus = aggregate_results(results)
```

#### Human-in-the-Loop Workflow
```python
class HumanInLoopWorkflow:
    def __init__(self):
        self.approval_queue = []
    
    async def execute(self, input_data: dict) -> dict:
        # AI generates draft
        draft = await ai_agent.generate(input_data)
        
        # Request human approval
        approval_id = await self.request_approval(draft)
        
        # Wait for human feedback
        feedback = await self.wait_for_approval(approval_id)
        
        if feedback['approved']:
            return await self.finalize(draft)
        else:
            # Revise based on feedback
            return await self.execute({
                **input_data,
                'feedback': feedback['comments']
            })
```

### 3.3 Production Patterns - Framework-Agnostic

#### Error Handling & Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustAgent:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def execute_with_retry(self, task: str):
        try:
            return await self.llm.generate(task)
        except RateLimitError:
            # Handle rate limits
            await asyncio.sleep(60)
            raise
        except Exception as e:
            logging.error(f"Agent execution failed: {e}")
            raise
```

#### Streaming Responses
```python
class StreamingAgent:
    async def stream_response(self, query: str):
        """Stream tokens as they're generated"""
        async for chunk in self.llm.stream(query):
            yield {
                "token": chunk,
                "timestamp": time.time()
            }

# FastAPI endpoint
@app.get("/api/chat/stream")
async def chat_stream(query: str):
    agent = StreamingAgent()
    
    async def generate():
        async for chunk in agent.stream_response(query):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamResponse(generate(), media_type="text/event-stream")
```

#### Caching for Efficiency
```python
from functools import lru_cache
import hashlib

class CachedAgent:
    def __init__(self, llm, cache_backend):
        self.llm = llm
        self.cache = cache_backend
    
    async def generate(self, prompt: str) -> str:
        # Create cache key
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Generate and cache
        result = await self.llm.generate(prompt)
        await self.cache.set(cache_key, result, ttl=3600)
        
        return result
```

#### Cost Optimization
```python
class CostOptimizedAgent:
    def __init__(self):
        self.cheap_model = "gpt-3.5-turbo"  # Fast, cheap
        self.smart_model = "gpt-4"  # Slow, expensive
    
    async def generate(self, query: str, complexity: str = "auto"):
        # Auto-detect complexity
        if complexity == "auto":
            complexity = await self.assess_complexity(query)
        
        if complexity == "simple":
            return await self.llm.generate(query, model=self.cheap_model)
        else:
            return await self.llm.generate(query, model=self.smart_model)
    
    async def assess_complexity(self, query: str) -> str:
        """Use cheap model to assess if we need expensive model"""
        assessment = await self.llm.generate(
            f"Is this a simple or complex query? {query}",
            model=self.cheap_model,
            max_tokens=10
        )
        return "simple" if "simple" in assessment.lower() else "complex"
```

### 3.4 Interview Talking Points - Transferable AI Patterns

**When discussing AI experience:**
- "I understand core agentic patterns - ReAct, CoT, RAG - regardless of framework"
- "I've implemented multi-agent orchestration workflows in production"
- "I design AI systems with error handling, streaming, and cost optimization"
- "I can work with any LLM API - OpenAI, Azure OpenAI, Claude, Gemini"

**Framework-Agnostic Knowledge:**
- Prompt engineering principles work across all LLMs
- RAG architecture is universal (embed, search, augment, generate)
- Agent patterns (ReAct, CoT) are conceptual, not framework-specific
- Workflow orchestration concepts apply whether using LangChain, custom code, or Temporal

**Production Considerations:**
- **Latency:** Streaming, caching, model selection
- **Cost:** Model routing, prompt optimization, caching
- **Reliability:** Retries, fallbacks, error handling
- **Observability:** Logging prompts, responses, token usage
- **Security:** Input validation, output filtering, PII handling

---

## Summary

As a senior or lead engineer targeting cross-stack roles, this chapter is meant to demonstrate:
- **Versatility:** contribute across backend (Go, Python) and reason clearly about enterprise frontend systems
- **Collaboration:** communicate effectively with Angular, platform, and backend teams
- **AI Expertise:** understand agentic workflows and production patterns independent of vendor
- **Leadership:** make practical architecture decisions across the full stack

**Focus Areas for Interview Prep:**
1. **Go:** read Go codebases, understand concurrency patterns, and discuss trade-offs vs Python
2. **TypeScript & Angular:** understand how enterprise frontend teams structure applications and consume APIs
3. **AI Patterns:** focus on concepts over frameworks; ReAct, RAG, and orchestration patterns transfer across platforms

You do not need to be an expert in every layer, but fluency in backend architecture plus credible understanding of Angular, TypeScript, and platform concerns positions you much better for lead-level full-stack roles.
