from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
page_html=(root/'web/index.html').read_text()
page_html=page_html.replace('<link rel="stylesheet" href="app.css">','<style>'+(root/'web/app.css').read_text()+'</style>')
page_html=page_html.replace('<script src="app.js" defer></script>','<script>'+(root/'web/app.js').read_text().replace('</script>','<\\/script>')+'</script>')
page_html=page_html.replace("<script>if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('./sw.js').catch(()=>{});</script>",'')
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for view in ({'width':1440,'height':900},{'width':390,'height':844}):
  page=browser.new_page(viewport=view)
  page.on('pageerror',lambda e: errors.append(str(e)))
  page.set_content(page_html,wait_until='load')
  page.wait_for_timeout(350)
  assert page.locator('.nav-item').count()==40,page.locator('.nav-item').count()
  if view['width']<600: page.locator('#menuButton').click()
  for name in ['mines','tower','threecard','roulette-us','roulette-fr','war','dragontiger','bingo','lotto','scratch','seven','dicepoker','treasure']:
   if view['width']<600 and not page.locator('.sidebar').evaluate('(el)=>el.classList.contains("open")'):page.locator('#menuButton').click()
   page.locator(f'[data-action="nav"][data-game="{name}"]').click()
   assert page.locator('#gameArea .panel').count()>=1,(view['width'],name)
   if name=='mines':
    page.locator('[data-action="mine-size"][data-value="100"]').click()
    assert page.locator('.mine-tile').count()==100
    page.locator('#minesRange').fill('33');page.locator('#minesRange').dispatch_event('change')
    assert page.locator('#minesCountValue').inner_text()=='33'
    page.locator('[data-action="mines-start"]').click()
    assert page.locator('.mine-tile:not([disabled])').count()==100
    page.locator('.mine-tile:not([disabled])').first.click()
   if name=='lotto':
    for n in range(1,7): page.locator(f'[data-action="lotto-pick"][data-value="{n}"]').click()
    page.locator('[data-action="lotto-play"]').click()
   if name=='dicepoker':page.locator('[data-action="dicepoker-roll"]').click()
   if name=='scratch':
    page.locator('[data-action="scratch-start"]').click()
    for i in range(9):page.locator(f'[data-action="scratch-open"][data-index="{i}"]').click()
   if name=='treasure':
    page.locator('[data-action="treasure-start"]').click()
    page.locator('[data-action="treasure-open"][data-index="4"]').click()
   if name=='seven':page.locator('[data-action="seven-bet"][data-value="double"]').click();page.locator('[data-action="seven-roll"]').click()
   if name=='threecard':page.locator('[data-action="three-deal"]').click();page.locator('[data-action="three-fold"]').click()
   if name=='bingo':page.locator('[data-action="bingo-play"]').click()
   if name=='dragonTiger':pass
  if view['width']<600: page.locator('#menuButton').click()
  page.locator('[data-action="nav"][data-game="sicbo"]').click()
  assert page.locator('[data-action="sicbo-pick"]').count()==35
  page.locator('[data-action="sicbo-pick"][data-value="sum-11"]').click()
  page.locator('[data-action="sicbo-roll"]').click()
  if view['width']<600: page.locator('#menuButton').click()
  page.locator('[data-action="nav"][data-game="craps"]').click()
  page.locator('[data-action="craps-pick"][data-value="dont"]').click()
  assert 'DON’T PASS' in page.locator('#gameArea').inner_text()
  page.locator('[data-action="craps-roll"]').click()
  page.locator('[data-action="mode-daily"]').click()
  assert 'РЕЖИМ ИГРЫ' in page.locator('#modeBar').inner_text()
  page.locator('[data-action="wallet"]').first.click()
  assert page.locator('.modal').count()==1
  page.keyboard.press('Escape');assert page.locator('.modal').count()==0
  page.screenshot(path=str(root/'releases'/f'ui_{view["width"]}.png'),full_page=False)
  print('PASS UI',view['width'],'40 nav items; all new screens and gameplay clicks')
  page.close()
 browser.close()

if errors: raise Exception('Browser page errors: '+repr(errors[:15]))
print('PASS no JavaScript page errors at 1440 and 390 widths')
