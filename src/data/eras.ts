/** Shared era configuration — used by index, archive pages, and tools. */

export const ERA_FOLDERS: Record<number, string> = {
  1:  '01_ancient_egypt_and_mesopotamia',
  2:  '02_ancient_greece_and_rome',
  3:  '03_the_middle_ages',
  4:  '04_renaissance_and_farthingales',
  5:  '05_baroque_and_rococo_panniers',
  6:  '06_victorian_era_crinolines',
  7:  '07_edwardian_sbend',
  8:  '08_1920s_flapper',
  9:  '09_1940s_rationing_and_new_look',
  10: '10_1960s_miniskirt',
  11: '11_1980s_power_dressing_and_puffballs',
  12: '12_21st_century_and_gender_neutrality',
};

export const ERA_SLUGS: Record<number, string> = {
  1:  'ancient-egypt-and-mesopotamia',
  2:  'ancient-greece-and-rome',
  3:  'the-middle-ages',
  4:  'renaissance-and-farthingales',
  5:  'baroque-and-rococo-panniers',
  6:  'victorian-era-crinolines',
  7:  'edwardian-s-bend',
  8:  '1920s-flapper',
  9:  '1940s-rationing-and-new-look',
  10: '1960s-mini-skirt',
  11: '1980s-power-dressing-and-puffballs',
  12: '21st-century-and-gender-neutrality',
};

/** Reverse lookup: slug → era_index */
export const SLUG_TO_INDEX: Record<string, number> = Object.fromEntries(
  Object.entries(ERA_SLUGS).map(([idx, slug]) => [slug, Number(idx)])
);
