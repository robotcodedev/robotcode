declare module "*.css" {
  const classes: string;
  export = classes;
}

declare module "*.ttf" {
  const content: File;
  export default content;
}
