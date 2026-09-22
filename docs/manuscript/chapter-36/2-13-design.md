---
title: "Design"
---

### 2.13 Design (Grind 75)
-   **Pattern:** Designing data structures that efficiently support specific operations. Often combines multiple data structures (hash map + doubly linked list, hash map + array, etc.) to achieve optimal time complexity for all operations.

#### 2.13.1 LRU Cache
**Problem:** Design a data structure that follows Least Recently Used (LRU) cache constraints. Implement `get(key)` and `put(key, value)` in O(1) time.

**Solution:** Combine a hash map (for O(1) lookups) with a doubly linked list (for O(1) insertions/deletions). The list maintains order by recency.

**Algorithm:**
- **get(key):** If key exists, move node to front (most recent) and return value. Otherwise return -1.
- **put(key, value):** If key exists, update and move to front. If not, add to front. If capacity exceeded, remove least recent (tail).

**Data Structures:**
- Hash map: `key → node`
- Doubly linked list: maintains recency order (most recent at head)

**Pseudocode:**
```
CLASS Node:
    key, value, prev, next

CLASS LRUCache:
    FUNCTION __init__(capacity):
        capacity = capacity
        cache = empty map
        left = new Node(0, 0)  // dummy head
        right = new Node(0, 0)  // dummy tail
        left.next = right
        right.prev = left
    
    FUNCTION remove(node):
        // Remove node from list
        prev, nxt = node.prev, node.next
        prev.next = nxt
        nxt.prev = prev
    
    FUNCTION insert(node):
        // Insert at right (most recent)
        prev = right.prev
        prev.next = node
        right.prev = node
        node.prev = prev
        node.next = right
    
    FUNCTION get(key):
        IF key in cache:
            remove(cache[key])
            insert(cache[key])
            RETURN cache[key].value
        RETURN -1
    
    FUNCTION put(key, value):
        IF key in cache:
            remove(cache[key])
        cache[key] = new Node(key, value)
        insert(cache[key])
        
        IF length of cache > capacity:
            lru = left.next
            remove(lru)
            DELETE cache[lru.key]
```

**Implementation:**
```python
class Node:
    def __init__(self, key=0, val=0):
        self.key = key
        self.val = val
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity: int):
        """
        Initialize LRU Cache with given capacity.
        """
        self.capacity = capacity
        self.cache = {}  # key -> node
        
        # Dummy head and tail
        self.left = Node(0, 0)
        self.right = Node(0, 0)
        self.left.next = self.right
        self.right.prev = self.left
    
    def remove(self, node: Node) -> None:
        """Remove node from linked list."""
        prev, nxt = node.prev, node.next
        prev.next = nxt
        nxt.prev = prev
    
    def insert(self, node: Node) -> None:
        """Insert node at right (most recent)."""
        prev = self.right.prev
        prev.next = node
        self.right.prev = node
        node.prev = prev
        node.next = self.right
    
    def get(self, key: int) -> int:
        """
        Time: O(1) - Hash map lookup + list operations.
        """
        if key in self.cache:
            self.remove(self.cache[key])
            self.insert(self.cache[key])
            return self.cache[key].val
        return -1
    
    def put(self, key: int, value: int) -> None:
        """
        Time: O(1) - Hash map operations + list operations.
        """
        if key in self.cache:
            self.remove(self.cache[key])
        
        self.cache[key] = Node(key, value)
        self.insert(self.cache[key])
        
        if len(self.cache) > self.capacity:
            # Remove LRU (leftmost)
            lru = self.left.next
            self.remove(lru)
            del self.cache[lru.key]
```

**Trace Table:**

| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | LRUCache(2), put(1,1), put(2,2), get(1), put(3,3), get(2) | [null, null, null, 1, null, -1] | Key 2 was evicted |
| Update | put(1,1), put(1,2), get(1) | [null, null, 2] | Value updated |
| Full capacity | put(1,1), put(2,2), put(3,3) (cap=2) | [null, null, null] | Key 1 evicted |
| Get refreshes | put(1,1), put(2,2), get(1), put(3,3), get(2) | [null, null, 1, null, -1] | get(1) saved key 1 |

#### 2.13.2 Time Based Key-Value Store
**Problem:** Design a time-based key-value store that can store multiple values for the same key at different timestamps and retrieve the key's value at a certain timestamp.

**Solution:** Use a hash map where each key maps to a list of `(timestamp, value)` pairs sorted by timestamp. Use binary search for retrieval.

**Algorithm:**
- **set(key, value, timestamp):** Append `(timestamp, value)` to key's list
- **get(key, timestamp):** Binary search for largest timestamp ≤ given timestamp

**Pseudocode:**
```
CLASS TimeMap:
    FUNCTION __init__():
        store = empty map  // key -> list of (timestamp, value)
    
    FUNCTION set(key, value, timestamp):
        IF key not in store:
            store[key] = []
        APPEND (timestamp, value) to store[key]
    
    FUNCTION get(key, timestamp):
        IF key not in store:
            RETURN ""
        
        values = store[key]
        // Binary search for largest timestamp <= given timestamp
        left, right = 0, length of values - 1
        result = ""
        
        WHILE left <= right:
            mid = (left + right) // 2
            IF values[mid][0] <= timestamp:
                result = values[mid][1]
                left = mid + 1
            ELSE:
                right = mid - 1
        
        RETURN result
```

**Implementation:**
```python
class TimeMap:
    def __init__(self):
        """
        Initialize time-based key-value store.
        """
        self.store = {}  # key -> list of (timestamp, value)
    
    def set(self, key: str, value: str, timestamp: int) -> None:
        """
        Time: O(1) - Append to list.
        """
        if key not in self.store:
            self.store[key] = []
        self.store[key].append((timestamp, value))
    
    def get(self, key: str, timestamp: int) -> str:
        """
        Time: O(log n) - Binary search on list of length n.
        """
        if key not in self.store:
            return ""
        
        values = self.store[key]
        left, right = 0, len(values) - 1
        result = ""
        
        # Binary search for largest timestamp <= given timestamp
        while left <= right:
            mid = (left + right) // 2
            if values[mid][0] <= timestamp:
                result = values[mid][1]
                left = mid + 1
            else:
                right = mid - 1
        
        return result
```

**Trace Table:**

| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | set("foo","bar",1), get("foo",1), get("foo",3) | [null, "bar", "bar"] | Timestamp 3 uses value from 1 |
| Multiple values | set("foo","bar",1), set("foo","bar2",4), get("foo",5) | [null, null, "bar2"] | Returns most recent ≤ 5 |
| No match | get("foo",0) | "" | No value at timestamp 0 |
| Exact match | set("a","b",10), get("a",10) | [null, "b"] | Exact timestamp match |

#### 2.13.3 Rectangle Grid Manager
**Problem:** Design a data structure to manage rectangles in an $n \times n$ grid. Implement:
- `add_rectangle(x, y, width, height)`: Add a rectangle at position (x, y) with given dimensions
- `remove_rectangle(x, y)`: Remove rectangle at any position within it
- `find_rectangle(x, y)`: Find rectangle at any position within it
- Validate that positions are within grid bounds

**Solution:** Use a 2D grid to track rectangle IDs, and a hash map to store rectangle metadata.

**Algorithm:**
- **Grid**: 2D array where each cell stores the rectangle ID (or None)
- **Metadata**: Hash map from rectangle ID to (x, y, width, height)
- **add_rectangle**: Mark all cells within rectangle bounds with unique ID
- **remove_rectangle**: Find rectangle ID at position, clear all its cells
- **find_rectangle**: Return rectangle ID at position

**Pseudocode:**
```
CLASS RectangleGrid:
    FUNCTION __init__(n):
        size = n
        grid = 2D array of size n×n filled with None
        rectangles = empty map  // rect_id -> (x, y, width, height)
        next_id = 1
    
    FUNCTION _is_valid(x, y):
        RETURN 0 <= x < size AND 0 <= y < size
    
    FUNCTION add_rectangle(x, y, width, height):
        // Validate bounds
        IF NOT _is_valid(x, y) OR NOT _is_valid(x + width - 1, y + height - 1):
            RAISE ValueError("Rectangle out of bounds")
        
        // Check for overlaps
        FOR i from x to x + width - 1:
            FOR j from y to y + height - 1:
                IF grid[i][j] is not None:
                    RAISE ValueError("Rectangle overlaps existing rectangle")
        
        // Add rectangle
        rect_id = next_id
        next_id += 1
        
        FOR i from x to x + width - 1:
            FOR j from y to y + height - 1:
                grid[i][j] = rect_id
        
        rectangles[rect_id] = (x, y, width, height)
        RETURN rect_id
    
    FUNCTION remove_rectangle(x, y):
        // Validate position
        IF NOT _is_valid(x, y):
            RAISE ValueError("Position out of bounds")
        
        rect_id = grid[x][y]
        IF rect_id is None:
            RAISE ValueError("No rectangle at position")
        
        // Get rectangle bounds and clear
        rx, ry, width, height = rectangles[rect_id]
        FOR i from rx to rx + width - 1:
            FOR j from ry to ry + height - 1:
                grid[i][j] = None
        
        DELETE rectangles[rect_id]
        RETURN rect_id
    
    FUNCTION find_rectangle(x, y):
        // Validate position
        IF NOT _is_valid(x, y):
            RAISE ValueError("Position out of bounds")
        
        rect_id = grid[x][y]
        IF rect_id is None:
            RETURN None
        
        RETURN rectangles[rect_id]
```

**Implementation:**
```python
class RectangleGrid:
    def __init__(self, n: int):
        """
        Initialize n×n grid.
        Time: O(n²) for grid initialization.
        Space: O(n²) for grid storage.
        """
        self.size = n
        self.grid = [[None for _ in range(n)] for _ in range(n)]
        self.rectangles = {}  # rect_id -> (x, y, width, height)
        self.next_id = 1
    
    def _is_valid(self, x: int, y: int) -> bool:
        """Check if position is within bounds."""
        return 0 <= x < self.size and 0 <= y < self.size
    
    def add_rectangle(self, x: int, y: int, width: int, height: int) -> int:
        """
        Add rectangle to grid.
        Time: O(width × height) to mark cells.
        Space: O(1) for metadata.
        """
        # Validate bounds
        if not self._is_valid(x, y) or not self._is_valid(x + width - 1, y + height - 1):
            raise ValueError(f"Rectangle out of bounds: ({x}, {y}) with size {width}×{height}")
        
        # Check for overlaps
        for i in range(x, x + width):
            for j in range(y, y + height):
                if self.grid[i][j] is not None:
                    raise ValueError(f"Rectangle overlaps existing rectangle at ({i}, {j})")
        
        # Add rectangle
        rect_id = self.next_id
        self.next_id += 1
        
        # Mark all cells
        for i in range(x, x + width):
            for j in range(y, y + height):
                self.grid[i][j] = rect_id
        
        # Store metadata
        self.rectangles[rect_id] = (x, y, width, height)
        return rect_id
    
    def remove_rectangle(self, x: int, y: int) -> int:
        """
        Remove rectangle containing position (x, y).
        Time: O(width × height) to clear cells.
        Space: O(1)
        """
        # Validate position
        if not self._is_valid(x, y):
            raise ValueError(f"Position out of bounds: ({x}, {y})")
        
        rect_id = self.grid[x][y]
        if rect_id is None:
            raise ValueError(f"No rectangle at position ({x}, {y})")
        
        # Get rectangle bounds
        rx, ry, width, height = self.rectangles[rect_id]
        
        # Clear all cells
        for i in range(rx, rx + width):
            for j in range(ry, ry + height):
                self.grid[i][j] = None
        
        # Remove metadata
        del self.rectangles[rect_id]
        return rect_id
    
    def find_rectangle(self, x: int, y: int) -> tuple | None:
        """
        Find rectangle at position (x, y).
        Time: O(1) for grid lookup.
        Space: O(1)
        """
        # Validate position
        if not self._is_valid(x, y):
            raise ValueError(f"Position out of bounds: ({x}, {y})")
        
        rect_id = self.grid[x][y]
        if rect_id is None:
            return None
        
        return self.rectangles[rect_id]
    
    def display_grid(self):
        """Display grid for debugging."""
        for row in self.grid:
            print([str(cell) if cell else '.' for cell in row])
```

**Usage Example:**
```python
# Create 5×5 grid
grid = RectangleGrid(5)

# Add rectangles
rect1 = grid.add_rectangle(0, 0, 2, 2)  # Top-left 2×2 rectangle
rect2 = grid.add_rectangle(3, 3, 2, 2)  # Bottom-right 2×2 rectangle

# Find rectangles
print(grid.find_rectangle(0, 0))  # (0, 0, 2, 2)
print(grid.find_rectangle(1, 1))  # (0, 0, 2, 2) - same rectangle
print(grid.find_rectangle(2, 2))  # None - empty cell

# Remove rectangle
grid.remove_rectangle(3, 4)  # Remove rect2 by any internal position

# Error handling
try:
    grid.add_rectangle(4, 4, 2, 2)  # Out of bounds
except ValueError as e:
    print(e)  # "Rectangle out of bounds..."
```

**Trace Table:**

| Operation | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| add_rectangle | (0, 0, 2, 2) | 1 | Added 2×2 rectangle at origin |
| find_rectangle | (1, 1) | (0, 0, 2, 2) | Found rectangle containing (1,1) |
| remove_rectangle | (0, 0) | 1 | Removed rectangle by any cell |
| find_rectangle | (0, 0) | None | Cell now empty |
| add_rectangle | (5, 5, 1, 1) | Error | Position out of bounds |

**Optimization Notes:**
- For sparse grids with many rectangles, consider using interval trees or R-trees
- For overlapping rectangles, use a list per cell instead of single ID
- For better remove/find performance, consider quadtree data structure

---

## When to Use Each Pattern

**Design Problems** typically involve:
- Combining multiple data structures
- Trading space for time (or vice versa)
- Maintaining invariants (like LRU order)
- Supporting multiple operations efficiently

**Common Combinations:**
- Hash Map + Doubly Linked List (LRU Cache)
- Hash Map + Array/List (Time Map, Design HashMap)
- Hash Map + Heap (Top K problems with updates)
- Multiple Hash Maps (Design Twitter, Multi-level caching)
