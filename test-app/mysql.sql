create database test;
use test;
create table sites(name varchar(255), url varchar(255));
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'password' WITH GRANT OPTION;