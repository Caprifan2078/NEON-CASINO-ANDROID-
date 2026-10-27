"""Local browser smoke, deliberately separate from native APK installation smoke."""
from pathlib import Path
import contextlib, http.server, socketserver, threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1] / 'web'
class Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args): pass
class Server(socketserver.TCPServer): allow_reuse_address=True

with Server(('127.0.0.1',0),Quiet) as server:
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_address[1]}'
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [390,1440]:
            ctx=browser.new_context(viewport={'width':width,'height':850},locale='ru-RU')
            page=ctx.new_page(); errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            html=(ROOT/'index.html').read_text()
            html=html.replace('  <meta http-equiv=\"Content-Security-Policy\"'+html.split('  <meta http-equiv=\"Content-Security-Policy\"',1)[1].split('>',1)[0]+'>','') if 'Content-Security-Policy' in html else html
            html=html.replace('<link rel=\"stylesheet\" href=\"app.css\">','<style>'+ (ROOT/'app.css').read_text() +'</style>')
            html=html.replace('<script src=\"app.js\" defer></script>','<script>'+ (ROOT/'app.js').read_text() +'</script>')
            page.set_content(html,wait_until='load',timeout=30000)
            page.wait_for_function("window.NEON_INFO && window.NEON_INFO.gameCount===44 && window.NEON_INFO.version==='1.7.5'",timeout=15000)
            assert page.locator('#gameNav .nav-item').count()==44,(width,page.locator('#gameNav .nav-item').count())
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'),width
            assert not errors,(width,errors)
            page.locator('button[data-action="mode-daily"]').first.click(force=True)
            assert page.evaluate("state.mode === 'daily' && state.balance===1000"),width
            page.locator('button[data-action="mode-free"]').first.click(force=True)
            assert page.evaluate("state.mode === 'free' && state.balance===50000"),width
            page.locator('button[data-action="quality-toggle"]').first.click(force=True)
            assert page.evaluate('document.documentElement.classList.contains("quality-lite")'),width
            assert not errors,(width,errors)
            print(f'PASS Chromium {width}px: 44 menus, mode isolation, quality toggle, no JS errors, no horizontal overflow')
            ctx.close()
        browser.close()
    server.shutdown()
