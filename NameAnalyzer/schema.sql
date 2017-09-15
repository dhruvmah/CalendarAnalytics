drop table if exists entries;
create table entries (
  id integer primary key autoincrement,
  firstname text not null,
  lastname text not null,
  gender text,
  probability text
);