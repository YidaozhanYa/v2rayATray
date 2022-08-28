# Maintainer: Yidaozhan Ya <yidaozhan_ya@outlook.com>

pkgname=v2raya-tray
pkgver=1.0
pkgrel=1
pkgdesc="Operate v2rayA in the system tray"
arch=('any')
url="https://github.com/YidaozhanYa/v2rayATray"
license=('MIT')
depends=('python' 'python-pyqt5' 'v2raya')
source=("git+https://github.com/YidaozhanYa/v2rayATray")
sha512sums=('SKIP')

package() {
  cd "v2rayATray"
  make DESTDIR="$pkgdir" install
}
