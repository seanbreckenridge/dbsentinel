CREATE TABLE animemetadata (
	json_data JSON, 
	id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	nsfw BOOLEAN, 
	approved_status VARCHAR NOT NULL, 
	media_type VARCHAR, 
	member_count INTEGER, 
	average_episode_duration INTEGER, 
	status_changed_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	PRIMARY KEY (id)
);
CREATE TABLE mangametadata (
	json_data JSON, 
	id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	nsfw BOOLEAN, 
	approved_status VARCHAR NOT NULL, 
	media_type VARCHAR, 
	member_count INTEGER, 
	average_episode_duration INTEGER, 
	status_changed_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	PRIMARY KEY (id)
);
CREATE TABLE proxiedimage (
	mal_id INTEGER NOT NULL, 
	mal_entry_type VARCHAR NOT NULL, 
	mal_url VARCHAR NOT NULL, 
	proxied_url VARCHAR NOT NULL, 
	PRIMARY KEY (mal_id, mal_entry_type)
);
CREATE INDEX ix_proxiedimage_mal_url ON proxiedimage (mal_url);
CREATE INDEX ix_proxiedimage_proxied_url ON proxiedimage (proxied_url);
CREATE TABLE anilistid (
	mal_id INTEGER NOT NULL, 
	entry_type VARCHAR NOT NULL, 
	anilist_id INTEGER NOT NULL, 
	PRIMARY KEY (mal_id, entry_type)
);
