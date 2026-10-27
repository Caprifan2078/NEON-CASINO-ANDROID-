from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
html=(root/'NEON_CASINO_IGRAT_OFFLINE.html').read_text(encoding='utf-8')
errs=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for w in [1440,390]:
  page=browser.new_page(viewport={'width':w,'height':780})
  page.set_default_timeout(6500)
  page.on('pageerror',lambda e:errs.append(str(e)))
  # Chromium in this environment blocks localhost; render inline with a deterministic Storage stand-in.
  page.goto('about:blank')
  page.evaluate("""() => Object.defineProperty(window,'localStorage',{configurable:true,value:{data:{},getItem(k){return this.data[k]??null},setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}}})""")
  page.set_content(html,wait_until='domcontentloaded')
  assert page.evaluate('window.NEON_INFO.version')=='1.7.2'
  assert page.evaluate('window.NEON_INFO.gameCount')==44
  assert page.locator('#gameNav .nav-item').count()==44
  assert page.locator('#gameSearch').get_attribute('placeholder').endswith('44…')
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2')
  for g in ['roulette','teenpatti','mines','fantan']:
   page.evaluate('g => navigate(g)',g)
   assert page.locator('#gameArea').inner_text().strip(),g
   assert page.locator('.nav-item.active').get_attribute('data-game')==g
  # Real wager + settlement, read same persisted chips from Storage.
  page.evaluate('navigate("coin")')
  page.locator('[data-action="coin-flip"]').click()
  page.wait_for_timeout(1100)
  browser_balance=page.evaluate('state.balance')
  saved_balance=page.evaluate('JSON.parse(localStorage.getItem("neon-casino-local-v1")).profiles.free.balance')
  assert browser_balance==saved_balance,(browser_balance,saved_balance)
  # Quality mode is still independent from game state.
  page.locator('#qualityToggle').click()
  assert page.evaluate('document.documentElement.classList.contains("quality-lite")')
  page.locator('#qualityToggle').click()
  assert not page.evaluate('document.documentElement.classList.contains("quality-lite")')
  print('PASS browser viewport',w,'game screens, settlement persistence, quality toggle, horizontal overflow')
  page.close()
 browser.close()
assert not errs,errs
print('ALL 1.7.2 BROWSER TESTS PASSED')
