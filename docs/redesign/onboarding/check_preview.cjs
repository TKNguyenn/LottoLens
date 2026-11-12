async sourcePage => {
const browser = sourcePage.context().browser();
for (const dpr of [1.25, 2]) {
  const context = await browser.newContext({viewport:{width:1360,height:850},deviceScaleFactor:dpr});
  try {
  const page = await context.newPage();
  const assert = (ok, why) => { if (!ok) throw new Error(why); };
  const get = id => page.locator('#' + id);
  const requests = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(request.url()));
  await page.goto('http://127.0.0.1:48631/lottolens-onboarding.html');
  if (await get('tour').isVisible()) await get('skip').click();
  if (await get('policy').isHidden()) await get('reset-button').click();
  assert(await get('policy').isVisible() && await get('tour').isHidden(), 'Policy first');
  await page.screenshot({path:'docs/redesign/onboarding/reviews/lottolens-onboarding-policy.png'});
  await get('read').check();
  assert(await get('accept').isDisabled(), 'Require both boxes');
  await get('agree').check();
  await get('accept').click();
  assert(await get('policy').isHidden() && await get('tour').isVisible(), 'Tour after policy');
  assert(await get('step-count').textContent() === 'Bước 1 / 8', 'First step');
  assert(await get('previous').isDisabled(), 'Back disabled on first step');
  await page.screenshot({path:'docs/redesign/onboarding/reviews/lottolens-onboarding-sharp-' + dpr + '.png'});
  for (const [lang, theme] of [['vi','dark'], ['vi','light'], ['en','light'], ['en','dark']]) {
    const root = page.locator('html');
    if (await root.getAttribute('lang') !== lang) await page.keyboard.press('l');
    if (await root.getAttribute('data-theme') !== theme) await page.keyboard.press('t');
    assert(await root.getAttribute('lang') === lang && await root.getAttribute('data-theme') === theme, 'Theme and language');
    const screenshots = new Set();
    for (let index = 0; index < 8; index++) {
      await get('step-nav').locator('button').nth(index).click();
      const image = get('shot-image');
      await image.evaluate(img => img.decode());
      const frame = await image.boundingBox();
      assert(frame.width > 260 && frame.height > 100, 'Unreadable screenshot');
      const resolution = await image.evaluate(img => [img.naturalWidth, img.naturalHeight, devicePixelRatio]);
      assert(Math.abs(resolution[2] - dpr) < .001 && resolution[0] + 1 >= frame.width * dpr && resolution[1] + 1 >= frame.height * dpr,
        `Browser enlarges a screenshot: ${lang}/${theme}/${index + 1}; expected DPR ${dpr}; actual ${resolution}; displayed ${frame.width}x${frame.height}`);
      const markers = await get('markers').locator('.marker').all();
      assert(markers.length === await get('instructions').locator('li').count(), 'Markers must match captions');
      for (const marker of markers) {
        const box = await marker.boundingBox();
        assert(box.x >= frame.x-1 && box.y >= frame.y-1 && box.x+box.width <= frame.x+frame.width+1 && box.y+box.height <= frame.y+frame.height+1, 'Marker outside image');
      }
      screenshots.add(await image.getAttribute('src'));
    }
    assert(screenshots.size === 8, 'Distinct screenshots per step');
  }
  await page.screenshot({path:'docs/redesign/onboarding/reviews/lottolens-onboarding-schedule.png'});
  await page.setViewportSize({width:390, height:740});
  const modal = await get('tour').boundingBox();
  assert(modal.width <= 390 && modal.y >= 0 && modal.y+modal.height <= 740, 'Modal outside narrow viewport');
  await page.screenshot({path:'docs/redesign/onboarding/reviews/lottolens-onboarding-mobile.png'});
  await get('previous').click();
  assert(await get('step-count').textContent() === 'Step 7 / 8', 'Back navigation');
  await get('next').click();
  await get('next').click();
  await page.reload();
  assert(await get('policy').isHidden() && await get('tour').isHidden(), 'Completed flow persists');
  await get('help').click();
  assert(await get('step-count').textContent() === 'Bước 1 / 8', 'Help reopens at the first step');
  await page.keyboard.press('Escape');
  assert(await get('tour').isHidden(), 'Escape closes Help');
  await get('reset-button').click();
  await get('exit-policy').click();
  assert(await get('exit-screen').isVisible(), 'Declining exits preview');
  await get('reopen').click();
  await get('read').check();
  await get('agree').check();
  await get('accept').click();
  await get('skip').click();
  await page.reload();
  assert(await get('tour').isHidden() && await get('policy').isHidden(), 'Skip persists');
  assert(!requests.some(url => /^https?:/.test(url) && !url.startsWith('http://127.0.0.1:48631/')), 'External request');
  assert(!errors.length, errors.join(', '));
  } finally { await context.close(); }
}
return 'Onboarding passed: all 32 step images at both DPR 1.25 and 2, no raster upscaling, policy, navigation, persistence, Help and reset.';
}
