DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    salary INTEGER NOT NULL,
    hire_date TEXT NOT NULL
);

INSERT INTO departments (id, name) VALUES
    (10, 'Engineering'),
    (20, 'Sales'),
    (30, 'Marketing'),
    (40, 'Support');

INSERT INTO employees (id, name, department_id, salary, hire_date) VALUES
    (1,  'Alice',   10, 95000, '2019-03-01'),
    (2,  'Bob',     10, 85000, '2020-06-15'),
    (3,  'Carol',   10, 85000, '2021-01-10'),
    (4,  'Dave',    10, 78000, '2022-09-01'),
    (5,  'Erin',    10, 71000, '2023-02-20'),
    (6,  'Frank',   20, 72000, '2018-11-05'),
    (7,  'Grace',   20, 69000, '2019-07-22'),
    (8,  'Heidi',   20, 69000, '2020-04-13'),
    (9,  'Ivan',    20, 61000, '2022-01-30'),
    (10, 'Judy',    30, 64000, '2021-05-18'),
    (11, 'Karl',    30, 58000, '2022-08-09'),
    (12, 'Liam',    30, 58000, '2023-03-11'),
    (13, 'Mia',     40, 55000, '2020-10-02'),
    (14, 'Noah',    40, 52000, '2021-12-19'),
    (15, 'Olivia',  40, 52000, '2022-06-07'),
    (16, 'Peter',   40, 49000, '2023-09-25');
