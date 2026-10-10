export function setTitle(title : undefined | string) {
	document.title = (typeof title === 'undefined' || title === '')
		? 'GoreeCloud Tasks'
		: `${title} | GoreeCloud Tasks`
}
