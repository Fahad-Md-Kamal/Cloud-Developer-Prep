---
title: "Backtracking"
---

### 2.10 Backtracking
-   **Pattern:** A recursive algorithm for solving problems by trying partial solutions and abandoning them if they don't lead to a valid solution (backtrack). Common in combination/permutation problems, puzzles, and constraint satisfaction.

**Backtracking Intuition:**

**The Core Idea:** Try, fail, undo, try again.

**Template:**
```python
def backtrack(state, choices):
    if is_solution(state):
        result.append(state.copy())
        return
    
    if should_prune(state):
        return  # Abandon this path
    
    for choice in choices:
        # Make choice
        state.add(choice)
        
        # Explore
        backtrack(state, remaining_choices)
        
        # Undo choice (backtrack!)
        state.remove(choice)
```

**When to use:**
- Generate all combinations/permutations
- Constraint satisfaction (Sudoku, N-Queens)
- Path finding with obstacles
- "Find all ways to..."

**Key Concepts:**
1. **Explore:** Try a choice
2. **Check:** Is it valid? Is it complete?
3. **Backtrack:** Undo and try next choice

#### 2.10.1 Combination Sum
**Problem:** Given an array of distinct integers `candidates` and a target `target`, return all unique combinations where the chosen numbers sum to `target`. The same number may be chosen unlimited times.

**Building Intuition:**

**Decision Tree:** At each step, for each candidate:
- **Take it:** Add to combination, continue (can reuse!)
- **Skip it:** Move to next candidate

**Example:** `candidates = [2, 3, 6, 7]`, `target = 7`
```
                    []
          /    /     \    \
        [2]  [3]    [6]  [7] ✓
       / \    |
    [2,2] [2,3]  [3,3]
      |     |      |
  [2,2,2] [2,3,2] [3,3,3]
    |       |  
 [2,2,2,2] [2,2,3] ✓
    |
[2,2,2,2,2] (>7, prune)
```

**Pruning:** Stop early if sum exceeds target.

**Why Backtracking?**
- Need to explore all possibilities
- Can prune invalid paths early
- Generate ALL solutions (not just one)

**Solution:** Use backtracking to explore all possible combinations.

**Algorithm:**
1. Start with an empty combination and remaining target
2. For each candidate:
   - Add it to current combination
   - Recursively try to reach remaining target
   - Backtrack by removing the candidate
3. Base cases:
   - If target == 0, we found a valid combination
   - If target < 0, invalid path

**Optimization:** Sort candidates and use a start index to avoid duplicates.

**Pseudocode:**
```
INITIALIZE result = []

FUNCTION backtrack(start, curr_combination, curr_sum):
    IF curr_sum == target:
        ADD copy of curr_combination to result
        RETURN
    IF curr_sum > target:
        RETURN
    
    FOR i from start to length of candidates:
        APPEND candidates[i] to curr_combination
        // Same number can be reused, so pass i (not i+1)
        backtrack(i, curr_combination, curr_sum + candidates[i])
        POP from curr_combination  // Backtrack

CALL backtrack(0, [], 0)
RETURN result
```

**Implementation:**
```python
def combination_sum(candidates: list[int], target: int) -> list[list[int]]:
    """
    Time: O(n^(t/m)) where n = len(candidates), t = target, m = min(candidates)
    Space: O(t/m) for recursion depth
    """
    res = []
    
    def backtrack(start, curr_combination, curr_sum):
        if curr_sum == target:
            res.append(curr_combination[:])  # Copy the combination
            return
        if curr_sum > target:
            return
        
        for i in range(start, len(candidates)):
            curr_combination.append(candidates[i])
            # Same number can be reused, so pass i (not i+1)
            backtrack(i, curr_combination, curr_sum + candidates[i])
            curr_combination.pop()  # Backtrack
    
    backtrack(0, [], 0)
    return res
```

**Trace Table:**
| Test Case | Candidates | Target | Output | Explanation |
|-----------|------------|--------|--------|-------------|
| Basic | [2,3,6,7] | 7 | [[2,2,3],[7]] | Two ways to sum to 7 |
| Multiple uses | [2,3,5] | 8 | [[2,2,2,2],[2,3,3],[3,5]] | Can reuse same number |
| Single candidate | [2] | 1 | [] | Cannot reach target |
| Exact match | [1] | 1 | [[1]] | Single element matches target |

#### 2.10.2 Word Search
**Problem:** Given an `m x n` board and a word, return `true` if the word exists in the grid. The word can be constructed from sequentially adjacent cells (no cell reuse).

**Solution:** Try starting from each cell, use DFS with backtracking.

**Algorithm:**
1. For each cell, start DFS if it matches the first letter
2. During DFS:
   - If we've matched all letters, return True
   - Mark current cell as visited (modify in place)
   - Try all 4 directions
   - Backtrack by unmarking the cell
3. Return False if no path found

**Key insight:** Modify the board to mark visited cells (change to '#'), then restore during backtracking.

**Pseudocode:**
```
FUNCTION dfs(r, c, i):
    // Found complete word
    IF i == length of word:
        RETURN True
    
    // Out of bounds or mismatch
    IF out of bounds OR board[r][c] != word[i]:
        RETURN False
    
    // Mark as visited
    tmp = board[r][c]
    board[r][c] = '#'
    
    // Try all 4 directions
    found = dfs(r+1, c, i+1) OR dfs(r-1, c, i+1) OR
            dfs(r, c+1, i+1) OR dfs(r, c-1, i+1)
    
    // Backtrack
    board[r][c] = tmp
    
    RETURN found

// Try starting from each cell
FOR each row r:
    FOR each col c:
        IF dfs(r, c, 0):
            RETURN True
RETURN False
```

**Implementation:**
```python
def exist(board: list[list[str]], word: str) -> bool:
    """
    Time: O(m * n * 4^L) where L is the length of word
    Space: O(L) for recursion depth
    """
    rows, cols = len(board), len(board[0])
    
    def dfs(r, c, i):
        # Found complete word
        if i == len(word):
            return True
        
        # Out of bounds or mismatch
        if (r < 0 or r >= rows or c < 0 or c >= cols or 
            board[r][c] != word[i]):
            return False
        
        # Mark as visited
        tmp = board[r][c]
        board[r][c] = '#'
        
        # Try all 4 directions
        found = (dfs(r + 1, c, i + 1) or
                 dfs(r - 1, c, i + 1) or
                 dfs(r, c + 1, i + 1) or
                 dfs(r, c - 1, i + 1))
        
        # Backtrack
        board[r][c] = tmp
        
        return found
    
    # Try starting from each cell
    for r in range(rows):
        for c in range(cols):
            if dfs(r, c, 0):
                return True
    
    return False
```

**Trace Table:**
| Test Case | Board | Word | Output | Explanation |
|-----------|-------|------|--------|-------------|
| Found | [["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]] | "ABCCED" | True | Path exists: A→B→C→C→E→D |
| Not found | [["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]] | "ABCB" | False | Cannot revisit B |
| Single cell | [["a"]] | "a" | True | Single character match |
| Diagonal not allowed | [["A","B"],["C","D"]] | "AD" | False | Can only move adjacent (not diagonal) |
