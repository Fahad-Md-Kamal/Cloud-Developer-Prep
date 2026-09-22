---
title: "Trees"
---

### 2.7 Trees
-   **Pattern:** Hierarchical data structures. Key patterns include tree traversal (DFS: pre-order, in-order, post-order; BFS: level-order), determining properties like height and diameter, and solving problems using recursion.

**Trees Intuition:**

**Key Concepts:**
1. **Recursive structure:** A tree is a root + left subtree + right subtree
2. **Traversals:**
   - **DFS:** Pre-order (root-left-right), In-order (left-root-right), Post-order (left-right-root)
   - **BFS:** Level by level (use queue)
3. **Base case:** Always check if node is None

**Common Patterns:**
- Height/Depth: `1 + max(left, right)`
- Diameter: Max of (left + right) at each node
- Path sum: Accumulate as you traverse
- Validation: Check property at each node

**When to use DFS vs BFS:**
- DFS (recursion): Height, validate, path problems
- BFS (queue): Level order, shortest path in tree

```python
# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

#### 2.7.1 Invert Binary Tree
**Problem:** Given the root of a binary tree, invert the tree, and return its root.

**Building Intuition:**

**The Idea:** Swap left and right children at every node.

**Visual:**
```
     4              4
   /   \    →      /   \
  2     7          7     2
 / \   / \        / \   / \
1   3 6   9      9   6 3   1
```

**Recursive Thinking:**
1. Base case: If node is None, return None
2. Invert left subtree
3. Invert right subtree
4. Swap left and right

**Why Recursion?**
- Tree is naturally recursive
- Each subtree is also a tree
- Elegant 3-line solution

**Solution:** Recursively swap the left and right children of each node. This is one of the most elegant recursive solutions.

**Algorithm:**
- Base case: if node is None, return None
- Swap the left and right children
- Recursively invert the left subtree
- Recursively invert the right subtree
- Return the root

**Pseudocode:**
```
FUNCTION invert_tree(root):
    IF root is None:
        RETURN None
    
    // Swap children
    root.left, root.right = root.right, root.left
    
    // Recurse on children
    invert_tree(root.left)
    invert_tree(root.right)
    
    RETURN root
```

**Implementation:**
```python
def invert_tree(root: TreeNode) -> TreeNode:
    """
    Time: O(n) - We visit every node.
    Space: O(h) - Where h is the height of the tree, for the recursion stack.
    """
    if not root:
        return None
        
    # Swap the children
    root.left, root.right = root.right, root.left
    
    # Recurse on the children
    invert_tree(root.left)
    invert_tree(root.right)
    
    return root
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic tree | [4,2,7,1,3,6,9] | [4,7,2,9,6,3,1] | All left/right children swapped |
| Left skewed | [1,2,null,3] | [1,null,2,null,3] | Becomes right-skewed |
| Single node | [1] | [1] | Single node unchanged |
| Empty tree | [] | [] | Empty tree returns empty |

#### 2.7.2 Maximum Depth of Binary Tree
**Problem:** Given the root of a binary tree, return its maximum depth (the number of nodes along the longest path from the root to a leaf).

**Solution:** Use recursion. The depth of a tree is 1 (for the current node) plus the maximum depth of its subtrees.

**Algorithm:**
- Base case: empty tree has depth 0
- Recursive case: `1 + max(depth(left), depth(right))`

**Pseudocode:**
```
FUNCTION max_depth(root):
    IF root is None:
        RETURN 0
    
    RETURN 1 + MAX(max_depth(root.left), max_depth(root.right))
```

**Implementation:**
```python
def max_depth(root: TreeNode) -> int:
    """
    Time: O(n) - We visit every node.
    Space: O(h) - For the recursion stack.
    """
    if not root:
        return 0
    
    return 1 + max(max_depth(root.left), max_depth(root.right))
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Balanced tree | [3,9,20,null,null,15,7] | 3 | Three levels: root, middle, leaves |
| Left skewed | [1,2,null,3] | 3 | Linear tree with depth 3 |
| Single node | [0] | 1 | Single node has depth 1 |
| Empty tree | [] | 0 | Empty tree has depth 0 |

#### 2.7.3 Same Tree
**Problem:** Given the roots of two binary trees, `p` and `q`, check if they are the same (same structure and node values).

**Solution:** Recursively compare nodes. Two trees are the same if:
1. Both are None (base case)
2. Both have the same value at the current node
3. Their left subtrees are the same
4. Their right subtrees are the same

**Algorithm:**
- If both are None, return True
- If one is None or values differ, return False
- Recursively check left and right subtrees

**Pseudocode:**
```
FUNCTION is_same_tree(p, q):
    IF p is None AND q is None:
        RETURN True
    IF p is None OR q is None OR p.val != q.val:
        RETURN False
    
    RETURN is_same_tree(p.left, q.left) AND is_same_tree(p.right, q.right)
```

**Implementation:**
```python
def is_same_tree(p: TreeNode, q: TreeNode) -> bool:
    """
    Time: O(min(p, q)) - We visit every node until we find a difference.
    Space: O(h) - Where h is the height of the taller tree.
    """
    if not p and not q:
        return True
    if not p or not q or p.val != q.val:
        return False
        
    return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)
```

**Trace Table:**

| Test Case | Input (p) | Input (q) | Output | Explanation |
|-----------|-----------|-----------|--------|-------------|
| Same trees | [1,2,3] | [1,2,3] | True | Identical structure and values |
| Different structure | [1,2] | [1,null,2] | False | Different tree structure |
| Different values | [1,2,1] | [1,1,2] | False | Same structure, different values |
| Both empty | [] | [] | True | Two empty trees are the same |

#### 2.7.4 Subtree of Another Tree
**Problem:** Given the roots of two binary trees, `root` and `subRoot`, return `true` if there is a subtree of `root` with the same structure and node values as `subRoot`.

**Solution:** Combine tree traversal with the "Same Tree" problem. At each node in the main tree, check if the subtree starting there matches `subRoot`.

**Algorithm:**
- If subRoot is None, it's always a subtree (edge case)
- If root is None but subRoot isn't, return False
- Check if the tree rooted at current node equals subRoot
- If not, recursively check left and right subtrees

**Pseudocode:**
```
FUNCTION is_subtree(root, subRoot):
    IF subRoot is None:
        RETURN True
    IF root is None:
        RETURN False
    
    IF is_same_tree(root, subRoot):
        RETURN True
    
    RETURN is_subtree(root.left, subRoot) OR is_subtree(root.right, subRoot)
```

**Implementation:**
```python
def is_subtree(root: TreeNode, subRoot: TreeNode) -> bool:
    """
    Time: O(m * n) - Check each node in main tree.
    Space: O(h) - Recursion depth.
    """
    if not subRoot:
        return True
    if not root:
        return False
    
    if is_same_tree(root, subRoot):
        return True
    
    return is_subtree(root.left, subRoot) or is_subtree(root.right, subRoot)
```

**Trace Table:**

| Test Case | Input (root) | Input (subRoot) | Output | Explanation |
|-----------|--------------|-----------------|--------|-------------|
| Is subtree | [3,4,5,1,2] | [4,1,2] | True | Subtree found |
| Not subtree | [3,4,5,1,2,null,null,null,null,0] | [4,1,2] | False | Structure doesn't match |
| Identical | [1,2,3] | [1,2,3] | True | Entire tree is subtree |
| Single node | [1] | [1] | True | Single nodes match |

#### 2.7.5 Diameter of Binary Tree
**Problem:** Given the root of a binary tree, return the length of the diameter (longest path between any two nodes).

**Solution:** Use DFS to compute height of each subtree. Diameter at each node is `left_height + right_height`.

**Pseudocode:**
```
INITIALIZE diameter = 0

FUNCTION dfs(node):
    IF node is None:
        RETURN 0
    
    left_height = dfs(node.left)
    right_height = dfs(node.right)
    
    diameter = MAX(diameter, left_height + right_height)
    
    RETURN 1 + MAX(left_height, right_height)

dfs(root)
RETURN diameter
```

**Implementation:**
```python
def diameter_of_binary_tree(root: TreeNode) -> int:
    """
    Time: O(n) - Visit each node once.
    Space: O(h) - Recursion stack depth.
    """
    diameter = 0
    
    def dfs(node):
        nonlocal diameter
        if not node:
            return 0
        
        left = dfs(node.left)
        right = dfs(node.right)
        
        diameter = max(diameter, left + right)
        
        return 1 + max(left, right)
    
    dfs(root)
    return diameter
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [1,2,3,4,5] | 3 | Path 4→2→1→3 (3 edges) |
| Left skewed | [1,2,null,3] | 2 | Path 3→2→1 (2 edges) |
| Single node | [1] | 0 | No edges |
| Balanced | [1,2,3,4,5,6,7] | 4 | Longest path crosses root |

#### 2.7.6 Balanced Binary Tree
**Problem:** Given a binary tree, determine if it is height-balanced (depth of two subtrees never differs by more than 1).

**Solution:** Use DFS to compute height and check balance simultaneously.

**Pseudocode:**
```
FUNCTION dfs(node):
    IF node is None:
        RETURN 0
    
    left_height = dfs(node.left)
    IF left_height == -1:
        RETURN -1  // Left subtree unbalanced
    
    right_height = dfs(node.right)
    IF right_height == -1:
        RETURN -1  // Right subtree unbalanced
    
    IF ABS(left_height - right_height) > 1:
        RETURN -1  // Current node unbalanced
    
    RETURN 1 + MAX(left_height, right_height)

RETURN dfs(root) != -1
```

**Implementation:**
```python
def is_balanced(root: TreeNode) -> bool:
    """
    Time: O(n) - Visit each node once.
    Space: O(h) - Recursion stack.
    """
    def dfs(node):
        if not node:
            return 0
        
        left = dfs(node.left)
        if left == -1:
            return -1
        
        right = dfs(node.right)
        if right == -1:
            return -1
        
        if abs(left - right) > 1:
            return -1
        
        return 1 + max(left, right)
    
    return dfs(root) != -1
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Balanced | [3,9,20,null,null,15,7] | True | All nodes balanced |
| Unbalanced | [1,2,2,3,3,null,null,4,4] | False | Left subtree too deep |
| Single node | [1] | True | Single node is balanced |
| Empty tree | [] | True | Empty tree is balanced |

#### 2.7.7 Minimum Height Trees
**Problem:** Given an undirected tree with `n` nodes, return all root labels that minimize the tree's height.

**Solution:** Trim leaf nodes layer by layer until 1-2 nodes remain (these are the centroids).

**Pseudocode:**
```
IF n <= 2:
    RETURN all nodes

// Build adjacency list
INITIALIZE adj = empty map, degrees = array of degrees
FOR each edge [a, b]:
    ADD b to adj[a], ADD a to adj[b]
    INCREMENT degrees[a], INCREMENT degrees[b]

// Find initial leaves
leaves = [node for node if degrees[node] == 1]

// Trim leaves layer by layer
remaining = n
WHILE remaining > 2:
    remaining -= length of leaves
    new_leaves = []
    FOR each leaf:
        neighbor = the only neighbor of leaf
        DECREMENT degrees[neighbor]
        IF degrees[neighbor] == 1:
            ADD neighbor to new_leaves
    leaves = new_leaves

RETURN leaves
```

**Implementation:**
```python
def find_min_height_trees(n: int, edges: list[list[int]]) -> list[int]:
    """
    Time: O(n) - Process each node once.
    Space: O(n) - Adjacency list storage.
    """
    if n <= 2:
        return list(range(n))
    
    # Build adjacency list
    adj = {i: set() for i in range(n)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    
    # Find initial leaves
    leaves = [i for i in range(n) if len(adj[i]) == 1]
    
    # Trim leaves layer by layer
    remaining = n
    while remaining > 2:
        remaining -= len(leaves)
        new_leaves = []
        for leaf in leaves:
            neighbor = adj[leaf].pop()
            adj[neighbor].remove(leaf)
            if len(adj[neighbor]) == 1:
                new_leaves.append(neighbor)
        leaves = new_leaves
    
    return leaves
```

**Trace Table:**

| Test Case | n | edges | Output | Explanation |
|-----------|---|-------|--------|-------------|
| Line | 4 | [[1,0],[1,2],[1,3]] | [1] | Node 1 is center |
| Path | 6 | [[3,0],[3,1],[3,2],[3,4],[5,4]] | [3,4] | Two centroids |
| Single | 1 | [] | [0] | Single node |
| Two nodes | 2 | [[0,1]] | [0,1] | Both are centroids |

---

### Continued: Additional Tree Problems

#### 2.7.8 Original Subtree Problem

```python
def is_subtree(root: TreeNode, subRoot: TreeNode) -> bool:
    """
    Time: O(m * n) - For each of m nodes in root, we might call is_same_tree (O(n)).
    Space: O(h_m) - Where h_m is the height of the main tree.
    """
    if not subRoot: return True
    if not root: return False
    
    if is_same_tree(root, subRoot):
        return True
        
    return is_subtree(root.left, subRoot) or is_subtree(root.right, subRoot)
```

**Trace Table:**

| Test Case | Input (root) | Input (subRoot) | Output | Explanation |
|-----------|--------------|-----------------|--------|-------------|
| Is subtree | [3,4,5,1,2] | [4,1,2] | True | subRoot found as left subtree |
| Not subtree | [3,4,5,1,2,null,null,null,null,0] | [4,1,2] | False | Extra node 0 breaks match |
| Same tree | [1,2,3] | [1,2,3] | True | Entire tree matches |
| Empty subRoot | [1] | [] | True | Empty tree is subtree of any tree |

#### 2.7.5 Lowest Common Ancestor of a Binary Search Tree
**Problem:** Given a BST, find the lowest common ancestor (LCA) of two given nodes `p` and `q`.

**Solution:** Leverage the BST property: left subtree values < root < right subtree values.

**Algorithm:**
- Start at root
- If both p and q are less than current node, LCA is in left subtree
- If both p and q are greater than current node, LCA is in right subtree
- Otherwise, current node is the LCA (it's the split point)

**Why this works:** The LCA is the first node where p and q diverge to different subtrees (or one of them is the current node).

**Pseudocode:**
```
INITIALIZE curr = root
WHILE curr is not None:
    IF p.val > curr.val AND q.val > curr.val:
        curr = curr.right  // Both in right subtree
    ELSE IF p.val < curr.val AND q.val < curr.val:
        curr = curr.left  // Both in left subtree
    ELSE:
        RETURN curr  // Found split point (LCA)
```

**Implementation:**
```python
def lowest_common_ancestor_bst(root: 'TreeNode', p: 'TreeNode', q: 'TreeNode') -> 'TreeNode':
    """
    Time: O(h) - Where h is height. O(log n) for balanced, O(n) for skewed.
    Space: O(1) - Iterative approach uses constant space.
    """
    curr = root
    while curr:
        if p.val > curr.val and q.val > curr.val:
            curr = curr.right
        elif p.val < curr.val and q.val < curr.val:
            curr = curr.left
        else:
            return curr
```

**Trace Table:**

| Test Case | Input (root) | p | q | Output | Explanation |
|-----------|--------------|---|---|--------|-------------|
| Both in subtrees | [6,2,8,0,4,7,9,null,null,3,5] | 2 | 8 | 6 | 2 is left of 6, 8 is right, so LCA is 6 |
| One is ancestor | [6,2,8,0,4,7,9,null,null,3,5] | 2 | 4 | 2 | 4 is descendant of 2, so LCA is 2 |
| Both in left | [6,2,8,0,4,7,9,null,null,3,5] | 0 | 4 | 2 | Both in left subtree, LCA is 2 |
| Simple tree | [2,1,3] | 1 | 3 | 2 | Root is the split point |

#### 2.7.6 Binary Tree Level Order Traversal
**Problem:** Given the root of a binary tree, return the level order traversal of its nodes' values (level by level, left to right).

**Solution:** Use BFS with a queue. Process all nodes at each level before moving to the next.

**Algorithm:**
1. Initialize queue with root
2. While queue is not empty:
   - Get the number of nodes at current level (queue size)
   - Process all nodes at this level:
     - Remove node from queue
     - Add its value to current level's list
     - Add its children to queue for next level
   - Add current level's list to result

**Pseudocode:**
```
IF root is None:
    RETURN []

INITIALIZE result = [], queue = [root]

WHILE queue is not empty:
    level_size = length of queue
    level = []
    FOR i from 0 to level_size:
        node = DEQUEUE from queue
        APPEND node.val to level
        IF node.left exists:
            ENQUEUE node.left
        IF node.right exists:
            ENQUEUE node.right
    APPEND level to result

RETURN result
```

**Implementation:**
```python
def level_order(root: TreeNode) -> list[list[int]]:
    """
    Time: O(n) - We visit each node once.
    Space: O(w) - Where w is the maximum width of the tree, for the queue.
    """
    if not root:
        return []

    res: list[list[int]] = []
    queue: list[TreeNode] = [root]
    head = 0  # index of the current node in the queue

    while head < len(queue):
        level_size = len(queue) - head
        level: list[int] = []
        for _ in range(level_size):
            node = queue[head]
            head += 1
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        res.append(level)

    return res
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic tree | [3,9,20,null,null,15,7] | [[3],[9,20],[15,7]] | Three levels traversed |
| Single node | [1] | [[1]] | Single level with one node |
| Left skewed | [1,2,null,3] | [[1],[2],[3]] | Each level has one node |
| Empty tree | [] | [] | Empty tree returns empty list |

#### 2.7.7 Validate Binary Search Tree
**Problem:** Given the root of a binary tree, determine if it is a valid BST.

**Solution:** Use DFS with boundary constraints. A valid BST requires that ALL nodes in the left subtree are less than the root, and ALL in the right are greater (not just immediate children).

**Algorithm:**
- Pass down valid range boundaries for each node
- For root, range is (-∞, +∞)
- For left child of node with value `val`, range becomes (-∞, val)
- For right child, range becomes (val, +∞)
- Check if current node's value is within its valid range

**Common mistake:** Only checking `left.val < root.val < right.val` is insufficient!

**Pseudocode:**
```
FUNCTION valid(node, left_boundary, right_boundary):
    IF node is None:
        RETURN True
    IF NOT (left_boundary < node.val < right_boundary):
        RETURN False
    
    RETURN valid(node.left, left_boundary, node.val) AND
           valid(node.right, node.val, right_boundary)

RETURN valid(root, -infinity, +infinity)
```

**Implementation:**
```python
def is_valid_bst(root: TreeNode) -> bool:
    """
    Time: O(n) - We visit each node once.
    Space: O(h) - For the recursion stack.
    """
    def valid(node, left_boundary, right_boundary):
        if not node:
            return True
        if not (left_boundary < node.val < right_boundary):
            return False
        
        return (valid(node.left, left_boundary, node.val) and
                valid(node.right, node.val, right_boundary))
                
    return valid(root, float("-inf"), float("inf"))
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Valid BST | [2,1,3] | True | All nodes satisfy BST property |
| Invalid (right subtree) | [5,1,4,null,null,3,6] | False | Node 3 in right subtree < root 5 |
| Valid single node | [1] | True | Single node is valid BST |
| Invalid duplicate | [1,1] | False | Duplicates violate strict inequality |

#### 2.7.8 Kth Smallest Element in a BST
**Problem:** Given the root of a BST and an integer `k`, return the `k`-th smallest value (1-indexed).

**Solution:** Use in-order traversal of BST, which visits nodes in sorted (ascending) order. Stop at the kth element.

**Algorithm (Iterative):**
1. Use a stack to simulate in-order traversal
2. Go as far left as possible, pushing nodes onto stack
3. Pop a node (this is the next smallest), increment counter
4. When counter equals k, return current node's value
5. Move to right child and repeat

**Why in-order?** In-order traversal of BST: left → root → right gives sorted order.

**Pseudocode:**
```
INITIALIZE stack = [], curr = root, n = 0

WHILE curr is not None OR stack is not empty:
    WHILE curr is not None:
        PUSH curr onto stack
        curr = curr.left
    
    curr = POP from stack
    INCREMENT n
    IF n == k:
        RETURN curr.val
    
    curr = curr.right
```

**Implementation:**
```python
def kth_smallest(root: TreeNode, k: int) -> int:
    """
    Time: O(H + k) - Where H is height to reach leftmost, then k iterations.
    Space: O(H) - For the stack.
    """
    stack = []
    curr = root
    n = 0
    
    while curr or stack:
        while curr:
            stack.append(curr)
            curr = curr.left
            
        curr = stack.pop()
        n += 1
        if n == k:
            return curr.val
        
        curr = curr.right
```

**Trace Table:**

| Test Case | Input | k | Output | Explanation |
|-----------|-------|---|--------|-------------|
| Basic BST | [3,1,4,null,2] | 1 | 1 | 1st smallest is 1 |
| Find middle | [5,3,6,2,4,null,null,1] | 3 | 3 | 3rd smallest is 3 |
| Find largest | [3,1,4,null,2] | 4 | 4 | 4th smallest (largest) is 4 |
| Small tree | [2,1] | 2 | 2 | 2nd smallest is root |

#### 2.7.9 Construct Binary Tree from Preorder and Inorder Traversal
**Problem:** Given `preorder` and `inorder` traversal arrays, construct and return the binary tree.

**Solution:** Use the properties of preorder and inorder traversals:
- **Preorder:** root → left → right (first element is always root)
- **Inorder:** left → root → right (root splits left and right subtrees)

**Algorithm:**
1. First element of preorder is the root
2. Find this root in inorder array
3. Elements to the left of root in inorder belong to left subtree
4. Elements to the right belong to right subtree
5. Recursively build left and right subtrees
6. Use a hashmap for O(1) lookup of root position in inorder

**Pseudocode:**
```
IF preorder OR inorder is empty:
    RETURN None

CREATE inorder_map from inorder (value -> index)
INITIALIZE preorder_idx = 0

FUNCTION build(left, right):
    IF left > right:
        RETURN None
    
    root_val = preorder[preorder_idx]
    INCREMENT preorder_idx
    root = new TreeNode(root_val)
    
    inorder_idx = inorder_map[root_val]
    
    root.left = build(left, inorder_idx - 1)
    root.right = build(inorder_idx + 1, right)
    RETURN root

RETURN build(0, length of inorder - 1)
```

**Implementation:**
```python
def build_tree(preorder: list[int], inorder: list[int]) -> TreeNode:
    """
    Time: O(n) - We visit each node once.
    Space: O(n) - For the inorder map and recursion stack.
    """
    if not preorder or not inorder:
        return None
        
    inorder_map = {val: i for i, val in enumerate(inorder)}
    preorder_idx = 0
    
    def build(left, right):
        nonlocal preorder_idx
        if left > right:
            return None
            
        root_val = preorder[preorder_idx]
        preorder_idx += 1
        root = TreeNode(root_val)
        
        inorder_idx = inorder_map[root_val]
        
        root.left = build(left, inorder_idx - 1)
        root.right = build(inorder_idx + 1, right)
        return root
        
    return build(0, len(inorder) - 1)
```

**Trace Table:**

| Test Case | Preorder | Inorder | Output | Explanation |
|-----------|----------|---------|--------|-------------|
| Basic tree | [3,9,20,15,7] | [9,3,15,20,7] | [3,9,20,null,null,15,7] | Tree reconstructed correctly |
| Left skewed | [1,2,3] | [3,2,1] | [1,2,null,3] | Left-skewed tree |
| Right skewed | [1,2,3] | [1,2,3] | [1,null,2,null,3] | Right-skewed tree |
| Single node | [1] | [1] | [1] | Single node tree |
