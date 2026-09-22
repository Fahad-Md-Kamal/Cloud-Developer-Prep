---
title: "Tries / Prefix Tree"
---

### 2.8 Tries (Prefix Tree)
-   **Pattern:** A tree-like data structure for efficient string operations. Each node represents a character, and paths from root to nodes spell out strings. Excellent for prefix matching, autocomplete, and dictionary operations.

```python
# Definition for a TrieNode.
class TrieNode:
    def __init__(self):
        self.children = {}  # Maps character to TrieNode
        self.is_end_of_word = False
```

#### 2.8.1 Implement Trie (Prefix Tree)
**Problem:** Implement a trie with `insert`, `search`, and `startsWith` methods.

**Solution:** Each node stores a map of children and a boolean flag indicating if it's the end of a word.

**Algorithm:**
- **Insert**: Iterate through characters, create nodes as needed, mark end of word
- **Search**: Traverse the trie; return true only if we reach a node marked as end of word
- **StartsWith**: Same as search, but don't require end-of-word marker

**Time Complexity:** All operations are O(m) where m is the length of the word/prefix.

**Pseudocode:**
```
CLASS TrieNode:
    children = empty map
    is_end_of_word = False

CLASS Trie:
    FUNCTION __init__():
        root = new TrieNode()
    
    FUNCTION insert(word):
        curr = root
        FOR each character c in word:
            IF c not in curr.children:
                curr.children[c] = new TrieNode()
            curr = curr.children[c]
        curr.is_end_of_word = True
    
    FUNCTION search(word):
        curr = root
        FOR each character c in word:
            IF c not in curr.children:
                RETURN False
            curr = curr.children[c]
        RETURN curr.is_end_of_word
    
    FUNCTION startsWith(prefix):
        curr = root
        FOR each character c in prefix:
            IF c not in curr.children:
                RETURN False
            curr = curr.children[c]
        RETURN True
```

**Implementation:**
```python
class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        """Insert a word into the trie. Time: O(m) where m = len(word)"""
        curr = self.root
        for c in word:
            if c not in curr.children:
                curr.children[c] = TrieNode()
            curr = curr.children[c]
        curr.is_end_of_word = True

    def search(self, word: str) -> bool:
        """Search for exact word. Time: O(m)"""
        curr = self.root
        for c in word:
            if c not in curr.children:
                return False
            curr = curr.children[c]
        return curr.is_end_of_word

    def startsWith(self, prefix: str) -> bool:
        """Check if any word starts with prefix. Time: O(m)"""
        curr = self.root
        for c in prefix:
            if c not in curr.children:
                return False
            curr = curr.children[c]
        return True
```

**Trace Table:**
| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic operations | insert("apple"), search("apple"), search("app") | [null, true, false] | "apple" found, "app" not complete word |
| Prefix check | insert("apple"), startsWith("app") | [null, true] | "app" is a valid prefix |
| Multiple words | insert("app"), insert("apple"), search("app") | [null, null, true] | Both "app" and "apple" stored |
| Not found | insert("dog"), search("cat") | [null, false] | "cat" never inserted |

#### 2.8.2 Design Add and Search Words Data Structure
**Problem:** Design a data structure supporting `addWord` and `search`. Search can include `.` wildcard matching any letter.

**Solution:** Extend the basic Trie with recursive DFS for wildcard handling.

**Algorithm for Search with Wildcards:**
- If character is not `.`, proceed normally
- If character is `.`, try all possible paths (all children)
- Use DFS to explore all possibilities when we hit a wildcard

**Why DFS?** We need to try all branches when we encounter `.`, which naturally maps to recursive exploration.

**Pseudocode:**
```
CLASS WordDictionary:
    FUNCTION __init__():
        root = new TrieNode()
    
    FUNCTION addWord(word):
        curr = root
        FOR each character c in word:
            IF c not in curr.children:
                curr.children[c] = new TrieNode()
            curr = curr.children[c]
        curr.is_end_of_word = True
    
    FUNCTION search(word):
        FUNCTION dfs(j, root):
            curr = root
            FOR i from j to length of word:
                c = word[i]
                IF c == '.':
                    // Try all possible children
                    FOR each child in curr.children.values():
                        IF dfs(i + 1, child):
                            RETURN True
                    RETURN False
                ELSE:
                    IF c not in curr.children:
                        RETURN False
                    curr = curr.children[c]
            RETURN curr.is_end_of_word
        
        RETURN dfs(0, root)
```

**Implementation:**
```python
class WordDictionary:
    def __init__(self):
        self.root = TrieNode()

    def addWord(self, word: str) -> None:
        """Add word to dictionary. Time: O(m)"""
        curr = self.root
        for c in word:
            if c not in curr.children:
                curr.children[c] = TrieNode()
            curr = curr.children[c]
        curr.is_end_of_word = True

    def search(self, word: str) -> bool:
        """
        Search with wildcard support. '.' matches any letter.
        Time: O(m * 26^w) where w is number of wildcards
        """
        def dfs(j, root):
            curr = root
            for i in range(j, len(word)):
                c = word[i]
                if c == ".":
                    # Try all possible children
                    for child in curr.children.values():
                        if dfs(i + 1, child):
                            return True
                    return False
                else:
                    if c not in curr.children:
                        return False
                    curr = curr.children[c]
            return curr.is_end_of_word
        return dfs(0, self.root)
```

**Trace Table:**
| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Exact match | addWord("bad"), search("bad") | [null, true] | Exact word found |
| Wildcard match | addWord("bad"), search(".ad") | [null, true] | '.' matches 'b' |
| Wildcard no match | addWord("bad"), search("b..") | [null, true] | Matches "bad" |
| Multiple wildcards | addWord("mad"), addWord("pad"), search(".ad") | [null, null, true] | Matches either word |

#### 2.8.3 Word Search II
**Problem:** Given an `m x n` board and a list of words, return all words on the board. Each word must be constructed from sequentially adjacent cells (no reuse of same cell).

**Solution:** Combine Trie with DFS/Backtracking. Build a trie from all words, then DFS from each board cell.

**Algorithm:**
1. Build a Trie containing all words
2. For each cell in the board:
   - Start DFS if the cell's character is in the trie
3. During DFS:
   - Mark current cell as visited
   - If we reach an end-of-word node, add word to results
   - Try all 4 directions (up, down, left, right)
   - Backtrack by unmarking the cell

**Why Trie + DFS?** The Trie lets us prune search paths early if no word has the current prefix.

**Pseudocode:**
```
// Build Trie
root = new TrieNode()
FOR each word in words:
    curr = root
    FOR each character c in word:
        IF c not in curr.children:
            curr.children[c] = new TrieNode()
        curr = curr.children[c]
    curr.is_end_of_word = True
    curr.word = word

// DFS on board
INITIALIZE result = [], visited = empty set

FUNCTION dfs(r, c, node):
    IF out of bounds OR (r,c) visited OR board[r][c] not in node.children:
        RETURN
    
    ADD (r, c) to visited
    node = node.children[board[r][c]]
    
    IF node.is_end_of_word:
        ADD node.word to result
        node.is_end_of_word = False  // Avoid duplicates
    
    // Try all 4 directions
    dfs(r+1, c, node)
    dfs(r-1, c, node)
    dfs(r, c+1, node)
    dfs(r, c-1, node)
    
    REMOVE (r, c) from visited

// Start DFS from each cell
FOR each row r:
    FOR each col c:
        dfs(r, c, root)

RETURN result
```

**Implementation:**
```python
def find_words(board: list[list[str]], words: list[str]) -> list[str]:
    """
    Time: O(m * n * 4^L) where L is max word length
    Space: O(W * L) for the trie, where W is number of words
    """
    # Build Trie
    root = TrieNode()
    for word in words:
        curr = root
        for c in word:
            if c not in curr.children:
                curr.children[c] = TrieNode()
            curr = curr.children[c]
        curr.is_end_of_word = True
        curr.word = word  # Store word at end node
    
    rows, cols = len(board), len(board[0])
    result = []
    visited = set()
    
    def dfs(r, c, node):
        if (r < 0 or r >= rows or c < 0 or c >= cols or 
            (r, c) in visited or board[r][c] not in node.children):
            return
        
        visited.add((r, c))
        node = node.children[board[r][c]]
        
        if node.is_end_of_word:
            result.append(node.word)
            node.is_end_of_word = False  # Avoid duplicates
        
        # Try all 4 directions
        dfs(r + 1, c, node)
        dfs(r - 1, c, node)
        dfs(r, c + 1, node)
        dfs(r, c - 1, node)
        
        visited.remove((r, c))
    
    # Start DFS from each cell
    for r in range(rows):
        for c in range(cols):
            dfs(r, c, root)
    
    return result
```

**Trace Table:**
| Test Case | Board | Words | Output | Explanation |
|-----------|-------|-------|--------|-------------|
| Basic | [["o","a","a","n"],["e","t","a","e"],["i","h","k","r"],["i","f","l","v"]] | ["oath","pea","eat","rain"] | ["eat","oath"] | Found "eat" and "oath" on board |
| Single cell | [["a"]] | ["a"] | ["a"] | Single character match |
| No match | [["a","b"],["c","d"]] | ["abcd"] | [] | Word cannot be formed |
| Multiple matches | [["a","b"],["c","d"]] | ["ab","cd"] | ["ab","cd"] | Both words found |
