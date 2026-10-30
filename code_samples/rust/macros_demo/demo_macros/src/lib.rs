//! A proc-macro crate: one derive, one attribute, one function-like macro.
//! Proc macros are ordinary Rust functions that take a TokenStream and return a TokenStream.

use proc_macro::TokenStream;
use quote::quote;
use syn::{Data, DeriveInput, Fields, ItemFn, LitStr, parse_macro_input};

/// `#[derive(Describe)]` adds `fn describe() -> String` that lists the struct's field names and types.
#[proc_macro_derive(Describe)]
pub fn derive_describe(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;
    let (impl_generics, ty_generics, where_clause) = ast.generics.split_for_impl();

    let fields = match &ast.data {
        Data::Struct(s) => match &s.fields {
            Fields::Named(f) => f.named.iter().collect::<Vec<_>>(),
            _ => {
                return syn::Error::new_spanned(&ast.ident, "Describe supports only structs with named fields")
                    .to_compile_error()
                    .into();
            }
        },
        _ => {
            return syn::Error::new_spanned(&ast.ident, "Describe can only be derived for structs")
                .to_compile_error()
                .into();
        }
    };

    let lines = fields.iter().map(|f| -> proc_macro2::TokenStream {
        let fname = f.ident.as_ref().unwrap().to_string();
        let ty = &f.ty;
        let ty_text = quote!(#ty).to_string().replace(' ', ""); // quote prints `Vec < String >`
        quote! { #fname.to_string() + ": " + #ty_text }
    });

    quote! {
        impl #impl_generics #name #ty_generics #where_clause {
            pub fn describe() -> String {
                let parts: Vec<String> = vec![ #(#lines),* ];
                format!("{} {{ {} }}", stringify!(#name), parts.join(", "))
            }
        }
    }
    .into()
}

/// `#[timed]` wraps a function so it prints how long each call took.
#[proc_macro_attribute]
pub fn timed(_args: TokenStream, item: TokenStream) -> TokenStream {
    let mut func = parse_macro_input!(item as ItemFn);
    let name = func.sig.ident.to_string();
    let body = &func.block;
    let new_body = quote! {
        {
            let __start = ::std::time::Instant::now();
            let __result = (|| #body)();
            println!("[timed] {} took {:?}", #name, __start.elapsed());
            __result
        }
    };
    func.block = syn::parse2(new_body).expect("valid block");
    quote!(#func).into()
}

/// `shout!("text")` is a function-like macro: it checks its input at compile time and expands to a string literal.
#[proc_macro]
pub fn shout(input: TokenStream) -> TokenStream {
    let lit = parse_macro_input!(input as LitStr);
    let text = lit.value();
    if text.is_empty() {
        return syn::Error::new(lit.span(), "shout! needs a non-empty string").to_compile_error().into();
    }
    let upper = text.to_uppercase();
    quote!(#upper).into()
}

/// `#[passthrough]` returns its input unchanged. Applied to `mod name;` (an out-of-line module)
/// it needs Rust 1.99 or newer; the macro receives the module's file contents as tokens.
#[proc_macro_attribute]
pub fn passthrough(_args: TokenStream, item: TokenStream) -> TokenStream {
    item
}
