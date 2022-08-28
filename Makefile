PREFIX = /usr

all:
	@echo Run \'make install\' to install v2rayA system tray.

install:
	@mkdir -p $(DESTDIR)$(PREFIX)/bin
	@cp -p v2raya_tray.py $(DESTDIR)$(PREFIX)/bin/v2raya_tray
	@chmod 755 $(DESTDIR)$(PREFIX)/bin/v2raya_tray

uninstall:
	@rm -rf $(DESTDIR)$(PREFIX)/bin/v2raya_tray
