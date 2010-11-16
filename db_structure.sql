CREATE TABLE registrations (
	id INTEGER NOT NULL,
	registered_jid varchar(256) NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE bitcoin_addresses (
	id INTEGER NOT NULL,
	address varchar(256) NOT NULL,
	registered_jid varchar(256) NOT NULL,
	PRIMARY KEY (id)
);
