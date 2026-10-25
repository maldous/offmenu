// The retained kitchen keeps its account tools. Its unsigned entry point uses
// the same dedicated, deployment-qualified sign-in page as the new landing.
document.addEventListener('click', event => {
  const button = event.target?.closest?.('#header-login');
  if (!button || !/^(?:log in|sign in)$/i.test(button.textContent.trim())) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  window.location.assign('/auth.html');
}, true);
