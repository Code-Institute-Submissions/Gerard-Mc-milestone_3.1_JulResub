// Resets all index.html variables so that when the user navigates to different pages and return to index.html,
// they are not met with a displayed search result box or modified placeholders from their previous use.
sessionStorage.setItem('name', 'Search Game');
sessionStorage.setItem('gpu', 'Search GPU');
sessionStorage.setItem('rating', '');
sessionStorage.setItem('appid', '');
sessionStorage.setItem('display', 'none');