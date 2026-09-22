---
title: "Graphs"
---

### 2.11 Graphs
-   **Pattern:** A graph consists of nodes (vertices) and edges connecting them. Key algorithms include DFS, BFS, and detecting cycles. Common representations: adjacency list or adjacency matrix.

**Graphs Intuition:**

**Key Concepts:**
1. **Representation:**
   - Adjacency list: `{node: [neighbors]}`
   - Adjacency matrix: 2D array
   - Grid: Treat as implicit graph

2. **Traversal:**
   - **DFS:** Explore as far as possible (use recursion/stack)
   - **BFS:** Explore level by level (use queue)

3. **Common Problems:**
   - Connected components (DFS/BFS)
   - Shortest path (BFS for unweighted)
   - Cycle detection (visited set + recursion stack)
   - Topological sort (DFS with finish times)

**DFS vs BFS:**
- DFS: Simpler, uses less memory, good for "any path"
- BFS: Finds shortest path, level-order processing

**Visited Set:** Critical to avoid infinite loops!

#### 2.11.1 Number of Islands
**Problem:** Given an `m x n` 2D grid of `'1'`s (land) and `'0'`s (water), return the number of islands. An island is formed by connecting adjacent lands horizontally or vertically.

**Building Intuition:**

**Key Insight:** Each '1' we find that hasn't been visited is a new island. Use DFS to mark all connected land.

**Example:**
```
1 1 0   →  Island 1
1 0 0
0 0 1   →  Island 2

Count: 2 islands
```

**Algorithm:**
1. Scan grid for '1'
2. When found: count++ and DFS to mark entire island
3. DFS marks '1' as visited (change to '0' or use visited set)
4. Continue scanning

**Why DFS?**
- Explore entire connected component
- Mark all land as visited
- Count each component once

**Solution:** Iterate through the grid. When we find a '1', increment island count and use DFS/BFS to mark all connected land as visited.

**Algorithm:**
1. Iterate through each cell
2. When we find unvisited land ('1'):
   - Increment island counter
   - Use DFS to mark entire island as visited
3. DFS marks current cell and recursively marks all adjacent land cells

**Pseudocode:**
```
IF grid is empty:
    RETURN 0

INITIALIZE islands = 0

FUNCTION dfs(r, c):
    IF out of bounds OR grid[r][c] != '1':
        RETURN
    
    grid[r][c] = '0'  // Mark as visited
    
    // Visit all 4 directions
    dfs(r+1, c)
    dfs(r-1, c)
    dfs(r, c+1)
    dfs(r, c-1)

FOR each row r:
    FOR each col c:
        IF grid[r][c] == '1':
            INCREMENT islands
            dfs(r, c)

RETURN islands
```

**Implementation:**
```python
def num_islands(grid: list[list[str]]) -> int:
    """
    Time: O(m * n) - Visit each cell once
    Space: O(m * n) - Worst case recursion depth if entire grid is one island
    """
    if not grid:
        return 0
    
    rows, cols = len(grid), len(grid[0])
    islands = 0
    
    def dfs(r, c):
        if (r < 0 or r >= rows or c < 0 or c >= cols or 
            grid[r][c] != '1'):
            return
        
        grid[r][c] = '0'  # Mark as visited
        
        # Visit all 4 directions
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)
    
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                islands += 1
                dfs(r, c)
    
    return islands
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Multiple islands | [["1","1","0"],["1","0","0"],["0","0","1"]] | 2 | Two separate islands |
| Single island | [["1","1","1"],["1","1","1"]] | 1 | All connected as one island |
| No islands | [["0","0"],["0","0"]] | 0 | No land at all |
| Diagonal not connected | [["1","0"],["0","1"]] | 2 | Diagonal cells are separate islands |

#### 2.11.2 Clone Graph
**Problem:** Given a reference of a node in a connected undirected graph, return a deep copy of the graph.

**Solution:** Use DFS or BFS with a hashmap to track original → clone mapping.

**Algorithm:**
1. Use a hashmap to store old_node → new_node mappings
2. DFS through the graph:
   - If node already cloned, return its clone
   - Create a new node (clone)
   - Add to hashmap
   - Recursively clone all neighbors
   - Add cloned neighbors to the new node's neighbors

**Pseudocode:**
```
IF node is None:
    RETURN None

INITIALIZE old_to_new = empty map

FUNCTION dfs(node):
    IF node in old_to_new:
        RETURN old_to_new[node]
    
    copy = new Node(node.val)
    old_to_new[node] = copy
    
    FOR each neighbor in node.neighbors:
        APPEND dfs(neighbor) to copy.neighbors
    
    RETURN copy

RETURN dfs(node)
```

**Implementation:**
```python
class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []

def clone_graph(node: 'Node') -> 'Node':
    """
    Time: O(V + E) - Visit each vertex and edge once
    Space: O(V) - Store all vertices in hashmap
    """
    if not node:
        return None
    
    old_to_new = {}
    
    def dfs(node):
        if node in old_to_new:
            return old_to_new[node]
        
        copy = Node(node.val)
        old_to_new[node] = copy
        
        for neighbor in node.neighbors:
            copy.neighbors.append(dfs(neighbor))
        
        return copy
    
    return dfs(node)
```

**Trace Table:**

| Test Case | Input (adjacency list) | Output | Explanation |
|-----------|------------------------|--------|-------------|
| Basic graph | [[2,4],[1,3],[2,4],[1,3]] | [[2,4],[1,3],[2,4],[1,3]] | 4-node graph cloned |
| Single node | [[]] | [[]] | Single node with no neighbors |
| Empty graph | [] | [] | Empty graph returns empty |
| Two nodes | [[2],[1]] | [[2],[1]] | Two connected nodes |

#### 2.11.3 Pacific Atlantic Water Flow
**Problem:** Given an `m x n` matrix of heights representing islands, find cells where water can flow to both the Pacific (top/left) and Atlantic (bottom/right) oceans. Water flows from higher or equal height cells.

**Solution:** Reverse the problem! Instead of starting from each cell, start from the ocean borders and flow inland (to higher elevations).

**Algorithm:**
1. Run DFS from Pacific border (top and left edges)
2. Run DFS from Atlantic border (bottom and right edges)
3. Cells reachable from both oceans are the answer
4. DFS flows to cells with height ≥ current (reverse flow)

**Why reverse?** Much more efficient than trying all paths from each cell.

**Pseudocode:**
```
IF heights is empty:
    RETURN []

INITIALIZE pacific = empty set, atlantic = empty set

FUNCTION dfs(r, c, visited, prev_height):
    IF (r,c) in visited OR out of bounds OR heights[r][c] < prev_height:
        RETURN
    
    ADD (r, c) to visited
    dfs(r+1, c, visited, heights[r][c])
    dfs(r-1, c, visited, heights[r][c])
    dfs(r, c+1, visited, heights[r][c])
    dfs(r, c-1, visited, heights[r][c])

// DFS from Pacific borders (top and left)
FOR each col c:
    dfs(0, c, pacific, heights[0][c])
    dfs(rows-1, c, atlantic, heights[rows-1][c])

FOR each row r:
    dfs(r, 0, pacific, heights[r][0])
    dfs(r, cols-1, atlantic, heights[r][cols-1])

RETURN [[r, c] for (r, c) in pacific ∩ atlantic]
```

**Implementation:**
```python
def pacific_atlantic(heights: list[list[int]]) -> list[list[int]]:
    """
    Time: O(m * n) - Visit each cell at most twice
    Space: O(m * n) - For the visited sets
    """
    if not heights:
        return []
    
    rows, cols = len(heights), len(heights[0])
    pacific = set()
    atlantic = set()
    
    def dfs(r, c, visited, prev_height):
        if ((r, c) in visited or r < 0 or r >= rows or 
            c < 0 or c >= cols or heights[r][c] < prev_height):
            return
        
        visited.add((r, c))
        dfs(r + 1, c, visited, heights[r][c])
        dfs(r - 1, c, visited, heights[r][c])
        dfs(r, c + 1, visited, heights[r][c])
        dfs(r, c - 1, visited, heights[r][c])
    
    # DFS from Pacific borders
    for c in range(cols):
        dfs(0, c, pacific, heights[0][c])
        dfs(rows - 1, c, atlantic, heights[rows - 1][c])
    
    for r in range(rows):
        dfs(r, 0, pacific, heights[r][0])
        dfs(r, cols - 1, atlantic, heights[r][cols - 1])
    
    return [[r, c] for r, c in pacific & atlantic]
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [[1,2,2,3,5],[3,2,3,4,4],[2,4,5,3,1],[6,7,1,4,5],[5,1,1,2,4]] | [[0,4],[1,3],[1,4],[2,2],[3,0],[3,1],[4,0]] | Water can flow to both oceans from these cells |
| Single row | [[1,2,3]] | [[0,2]] | Only rightmost cell reaches both |
| Single cell | [[1]] | [[0,0]] | Single cell touches all borders |
| Uniform height | [[2,2],[2,2]] | [[0,0],[0,1],[1,0],[1,1]] | All cells reach both oceans |

#### 2.11.4 Accounts Merge (Grind 75)
**Problem:** Given a list of accounts where each account contains a name and a list of email addresses, merge accounts that belong to the same person (identified by common emails).

**Solution:** Use Union-Find (Disjoint Set Union) or DFS to connect emails that belong to the same person.

**Algorithm (DFS approach):**
1. Build a graph where edges connect emails from the same account
2. Use DFS to find connected components (each is one person)
3. Sort emails within each component and add the name

**Pseudocode:**
```
// Build graph
INITIALIZE email_to_name = map from email to name
INITIALIZE graph = adjacency list of emails

FOR each account:
    name = account[0]
    emails = account[1:]
    FOR each email in emails:
        email_to_name[email] = name
        IF this is not the first email:
            ADD edge between first email and current email

// Find connected components using DFS
INITIALIZE visited = empty set
INITIALIZE result = []

FUNCTION dfs(email, component):
    visited.add(email)
    component.add(email)
    FOR each neighbor in graph[email]:
        IF neighbor not in visited:
            dfs(neighbor, component)

FOR each email:
    IF email not in visited:
        component = empty set
        dfs(email, component)
        sorted_emails = sorted list of component
        name = email_to_name[email]
        ADD [name] + sorted_emails to result

RETURN sorted result
```

**Implementation:**
```python
def accounts_merge(accounts: list[list[str]]) -> list[list[str]]:
    """
    Time: O(N * K * log(K)) where N is number of accounts, K is max emails per account
    Space: O(N * K) for graph and visited set
    """
    from collections import defaultdict
    
    # Build graph
    email_to_name = {}
    graph = defaultdict(list)
    
    for account in accounts:
        name = account[0]
        first_email = account[1]
        
        for email in account[1:]:
            email_to_name[email] = name
            graph[first_email].append(email)
            graph[email].append(first_email)
    
    # DFS to find connected components
    visited = set()
    result = []
    
    def dfs(email, component):
        visited.add(email)
        component.add(email)
        for neighbor in graph[email]:
            if neighbor not in visited:
                dfs(neighbor, component)
    
    for email in email_to_name:
        if email not in visited:
            component = set()
            dfs(email, component)
            sorted_emails = sorted(component)
            result.append([email_to_name[email]] + sorted_emails)
    
    return sorted(result)
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic merge | [["John","john@mail.com","john_work@mail.com"],["John","john@mail.com","john_home@mail.com"]] | [["John","john@mail.com","john_home@mail.com","john_work@mail.com"]] | Two accounts merged via common email |
| No merge | [["John","a@mail.com"],["Mary","b@mail.com"]] | [["John","a@mail.com"],["Mary","b@mail.com"]] | Different people, no merge |
| Chain merge | [["A","a@mail.com","b@mail.com"],["A","b@mail.com","c@mail.com"]] | [["A","a@mail.com","b@mail.com","c@mail.com"]] | Transitive merge |
| Same name, different people | [["John","a@mail.com"],["John","b@mail.com"]] | [["John","a@mail.com"],["John","b@mail.com"]] | Same name but different emails |

#### 2.11.5 Course Schedule
**Problem:** There are `numCourses` courses labeled from `0` to `numCourses-1`. You are given an array `prerequisites` where `prerequisites[i] = [ai, bi]` means you must take course `bi` first to take course `ai`. Return `true` if you can finish all courses.

**Solution:** This is cycle detection in a directed graph. Use DFS with three states: unvisited, visiting, visited.

**Algorithm:**
1. Build adjacency list from prerequisites
2. For each course, run DFS:
   - Mark as "visiting" (in current path)
   - Visit all prerequisites
   - If we see a "visiting" node, there's a cycle
   - Mark as "visited" when done
3. If we find a cycle, return False

**States:**
- 0: unvisited
- 1: visiting (in current DFS path)
- 2: visited (completely processed)

**Pseudocode:**
```
// Build adjacency list
INITIALIZE graph = {i: [] for i in range(numCourses)}
FOR each [course, prereq] in prerequisites:
    ADD prereq to graph[course]

// 0 = unvisited, 1 = visiting, 2 = visited
INITIALIZE state = [0] * numCourses

FUNCTION has_cycle(course):
    IF state[course] == 1:  // Cycle detected
        RETURN True
    IF state[course] == 2:  // Already processed
        RETURN False
    
    state[course] = 1  // Mark as visiting
    FOR each prereq in graph[course]:
        IF has_cycle(prereq):
            RETURN True
    state[course] = 2  // Mark as visited
    
    RETURN False

FOR i from 0 to numCourses:
    IF has_cycle(i):
        RETURN False

RETURN True
```

**Implementation:**
```python
def can_finish(numCourses: int, prerequisites: list[list[int]]) -> bool:
    """
    Time: O(V + E) - Visit each course and prerequisite once
    Space: O(V + E) - For the adjacency list and recursion
    """
    # Build adjacency list
    graph = {i: [] for i in range(numCourses)}
    for course, prereq in prerequisites:
        graph[course].append(prereq)
    
    # 0 = unvisited, 1 = visiting, 2 = visited
    state = [0] * numCourses
    
    def has_cycle(course):
        if state[course] == 1:  # Cycle detected
            return True
        if state[course] == 2:  # Already processed
            return False
        
        state[course] = 1  # Mark as visiting
        for prereq in graph[course]:
            if has_cycle(prereq):
                return True
        state[course] = 2  # Mark as visited
        
        return False
    
    for i in range(numCourses):
        if has_cycle(i):
            return False
    
    return True
```

**Trace Table:**

| Test Case | numCourses | Prerequisites | Output | Explanation |
|-----------|------------|---------------|--------|-------------|
| No cycle | 2 | [[1,0]] | True | Course 1 requires course 0 (no cycle) |
| Has cycle | 2 | [[1,0],[0,1]] | False | Circular dependency detected |
| Independent courses | 3 | [[1,0],[2,0]] | True | Multiple courses can depend on same prereq |
| No prerequisites | 5 | [] | True | No dependencies at all |

#### 2.11.5 Number of Connected Components in an Undirected Graph
**Problem:** Given `n` nodes labeled from `0` to `n-1` and a list of undirected edges, return the number of connected components.

**Solution:** Use Union-Find (Disjoint Set Union) or DFS/BFS to count components.

**Algorithm (Union-Find):**
1. Initially, each node is its own component
2. For each edge, union the two nodes
3. Count the number of distinct root parents

**Union-Find operations:**
- **Find:** Get the root parent of a node (with path compression)
- **Union:** Connect two components by linking their roots

**Pseudocode:**
```
INITIALIZE parent = [0, 1, 2, ..., n-1]
INITIALIZE rank = [1, 1, 1, ..., 1]

FUNCTION find(node):
    // Path compression
    IF parent[node] != node:
        parent[node] = find(parent[node])
    RETURN parent[node]

FUNCTION union(n1, n2):
    p1 = find(n1)
    p2 = find(n2)
    IF p1 == p2:
        RETURN 0  // Already connected
    
    // Union by rank
    IF rank[p1] > rank[p2]:
        parent[p2] = p1
        rank[p1] += rank[p2]
    ELSE:
        parent[p1] = p2
        rank[p2] += rank[p1]
    
    RETURN 1  // Reduced component count by 1

INITIALIZE components = n
FOR each [n1, n2] in edges:
    components -= union(n1, n2)

RETURN components
```

**Implementation:**
```python
def count_components(n: int, edges: list[list[int]]) -> int:
    """
    Time: O(E * α(n)) where α is inverse Ackermann (nearly constant)
    Space: O(n) - For parent array
    """
    parent = list(range(n))
    rank = [1] * n
    
    def find(node):
        # Path compression
        if parent[node] != node:
            parent[node] = find(parent[node])
        return parent[node]
    
    def union(n1, n2):
        p1, p2 = find(n1), find(n2)
        if p1 == p2:
            return 0  # Already connected
        
        # Union by rank
        if rank[p1] > rank[p2]:
            parent[p2] = p1
            rank[p1] += rank[p2]
        else:
            parent[p1] = p2
            rank[p2] += rank[p1]
        
        return 1  # Reduced component count by 1
    
    components = n
    for n1, n2 in edges:
        components -= union(n1, n2)
    
    return components
```

**Trace Table:**

| Test Case | n | Edges | Output | Explanation |
|-----------|---|-------|--------|-------------|
| Multiple components | 5 | [[0,1],[1,2],[3,4]] | 2 | Two groups: {0,1,2} and {3,4} |
| All connected | 5 | [[0,1],[1,2],[2,3],[3,4]] | 1 | All nodes in one component |
| No edges | 4 | [] | 4 | Each node is its own component |
| Single node | 1 | [] | 1 | Single isolated node |
