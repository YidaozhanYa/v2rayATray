PREFIX = /usr

all:
	@echo Run \'make install\' to install v2rayA system tray.

install:
	@mkdir -p $(DESTDIR)$(PREFIX)/bin
	@mkdir -p $(DESTDIR)$(PREFIX)/share/applications
	@cp -p v2raya_tray.py $(DESTDIR)$(PREFIX)/bin/v2raya_tray
	@chmod 755 $(DESTDIR)$(PREFIX)/bin/v2raya_tray
	@cp -p v2raya_tray.desktop $(DESTDIR)$(PREFIX)/share/applications/v2raya_tray.desktop

uninstall:
	@rm -rf $(DESTDIR)$(PREFIX)/bin/v2raya_tray
	@rm -rf $(DESTDIR)$(PREFIX)/share/applications/v2raya_tray.desktop
