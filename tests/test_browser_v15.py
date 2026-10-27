from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
html=(root/'web/index.html').read_text().replace('<link rel="stylesheet" href="app.css">','<style>'+(root/'web/app.css').read_text()+'</style>')
html=html.replace('<script src="app.js" defer></script>','<script>'+(root/'web/app.js').read_text().replace('</script>','<\\/script>')+'</script>')
html=html.replace("<script>if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('./sw.js').catch(()=>{});</script>",'')
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width in (1440,390):
  page=browser.new_page(viewport={'width':width,'height':900})
  page.on('pageerror',lambda e: errors.append(str(e)))
  page.set_content(html,wait_until='load')
  assert page.locator('.nav-item').count()==40
  # Navigate through actual sidebar UI on both screen widths.
  for game in ['andar','reddog','pick3','bingo90','keno80','cardsuit','ladder','slots5','holdem','letitride','rps','colors']:
   if width==390 and not page.locator('.sidebar').evaluate('(e)=>e.classList.contains("open")'):
    page.locator('#menuButton').click()
   page.locator(f'.nav-item[data-game="{game}"]').click()
   assert page.locator('#gameArea .panel').count()>0,(width,game)
   # Each game must be genuinely clickable and wagered, not an empty placeholder.
   if game=='andar':page.locator('[data-action="andar-play"]').click()
   elif game=='reddog':page.locator('[data-action="reddog-play"]').click()
   elif game=='pick3':page.locator('[data-action="pick3-step"]').first.click();page.locator('[data-action="pick3-style"][data-value="box"]').click();page.locator('[data-action="pick3-play"]').click()
   elif game=='bingo90':page.locator('[data-action="bingo90-play"]').click();assert page.locator('.b90-cell').count()==27
   elif game=='keno80':
    for i in range(1,7):page.locator(f'[data-action="keno80-pick"][data-value="{i}"]').click()
    page.locator('[data-action="keno80-play"]').click()
   elif game=='cardsuit':page.locator('[data-action="cardsuit-pick"][data-value="ace"]').click();page.locator('[data-action="cardsuit-play"]').click()
   elif game=='ladder':
    page.locator('[data-action="ladder-start"]').click();assert page.locator('[data-action="ladder-next"]').count()==1
    page.locator('[data-action="ladder-next"]').click()
    if page.locator('[data-action="ladder-cash"]:not([disabled])').count():page.locator('[data-action="ladder-cash"]').click()
   elif game=='slots5':page.locator('[data-action="slots5-spin"]').click();assert page.locator('.slots5-reel').count()==5
   elif game=='holdem':page.locator('[data-action="holdem-play"]').click()
   elif game=='letitride':
    page.locator('[data-action="letitride-start"]').click();page.locator('[data-action="letitride-pull"]').click();page.locator('[data-action="letitride-ride"]').click()
    assert page.locator('[data-action="letitride-start"]').count()==1
   elif game=='rps':page.locator('[data-action="rps-pick"][data-value="paper"]').click();page.locator('[data-action="rps-play"]').click()
   elif game=='colors':page.locator('[data-action="colors-count"][data-value="two"]').click();page.locator('[data-action="colors-play"]').click()
   assert page.locator('#balanceText').inner_text()
  page.screenshot(path=str(root/'releases'/f'neon_v15_{width}.png'),full_page=False)
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+2'),f'horizontal scroll on {width}'
  print('PASS Chromium',width,'12 actual new game flows, 40 nav entries, valid balance, no horizontal overflow')
  page.close()
 browser.close()
assert not errors,errors
print('PASS no uncaught JavaScript errors')
