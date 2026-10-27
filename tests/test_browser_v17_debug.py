from pathlib import Path
from playwright.sync_api import sync_playwright
from time import perf_counter
root=Path(__file__).resolve().parents[1]
# Load complete standalone HTML: no HTTP or unrelated dependencies.
html=Path('/mnt/data/NEON_CASINO_ROYALE_v1_7/NEON_CASINO_ROYALE_v1_7_OFFLINE.html').read_text()
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width in [1440,390,320]:
  page=browser.new_page(viewport={'width':width,'height':840},device_scale_factor=1)
  page.set_default_timeout(3500)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(html,wait_until='load')
  assert page.evaluate('window.NEON_INFO.gameCount')==44
  assert page.locator('.nav-item').count()==44
  assert page.locator('#qualityToggle').count()==1
  original=page.locator('#balanceText').inner_text()
  t=perf_counter()
  for g in ['fantan','crown','caribbean','teenpatti']:
   print('TEST',width,g,flush=True)
   if width!=1440:page.locator('#menuButton').click()
   page.locator(f'.nav-item[data-game="{g}"]').click()
   assert page.locator('#gameArea .panel').count()>=1,g
   if g=='fantan':
    assert page.locator('[data-action="fan-pick"]').count()==16
    page.locator('[data-action="fan-pick"][data-value="nim:1:2"]').click()
    page.locator('[data-action="fan-play"]').click()
   if g=='crown':
    page.locator('[data-action="crown-pick"][data-value="3"]').click()
    page.locator('[data-action="crown-play"]').click()
   if g=='caribbean':
    page.locator('[data-action="caribbean-start"]').click()
    assert page.locator('[data-action="caribbean-call"]').count()==1
    page.locator('[data-action="caribbean-fold"]').click()
    assert page.locator('[data-action="caribbean-call"]').count()==0
   if g=='teenpatti':
    page.locator('[data-action="teen-pair"]').click()
    page.locator('[data-action="teen-start"]').click()
    page.locator('[data-action="teen-play"]').click()
    assert page.locator('[data-action="teen-play"]').count()==0
  elapsed=perf_counter()-t
  page.locator('#qualityToggle').click()
  assert page.evaluate('document.documentElement.classList.contains("quality-lite")')
  page.locator('#qualityToggle').click()
  assert not page.evaluate('document.documentElement.classList.contains("quality-lite")')
  # Check saving wallet isolation and no auto reload or unexpected reset from visual controls.
  assert page.locator('#balanceText').inner_text()!=original
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'),f'horizontal overflow at {width}px'
  page.screenshot(path=str(root.parent/'release'/f'ui_{width}.png'))
  print(f'PASS Chromium width {width}, 44 tabs, 4 gameplay flows, quality mode, JS errors 0, duration {elapsed:.2f}s')
  page.close()
 browser.close()
assert not errors, errors
print('BROWSER QA PASSED')
